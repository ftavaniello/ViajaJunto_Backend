from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.adapters.outbound.email.email_sender_memory import EmailSenderMemory
from app.adapters.outbound.persistence.convite_viagem_model import ConviteViagemModel
from app.adapters.outbound.persistence.membro_viagem_repository_sqlalchemy import (
    SQLAlchemyMembroViagemRepository,
)
from app.adapters.outbound.persistence.unit_of_work_sqlalchemy import SQLAlchemyUnitOfWork
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.persistence.viagem_model import MembroViagemModel
from app.adapters.outbound.persistence.viagem_repository_sqlalchemy import (
    SQLAlchemyViagemRepository,
)
from app.application.use_cases.criar_viagem import CriarViagem
from app.domain.entities.usuario import Usuario
from app.domain.enums import PapelMembro
from app.domain.errors import MembroJaParticipa
from app.infrastructure.config import settings
from app.infrastructure.database import get_db
from app.infrastructure.dependencies import get_token_service
from app.infrastructure.email import get_email_sender
from app.main import app


@pytest.fixture
def email_sender() -> EmailSenderMemory:
    return EmailSenderMemory()


@pytest.fixture
def client(db_session, email_sender):
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    app.dependency_overrides[get_email_sender] = lambda: email_sender
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def cenario(db_session, email_teste):
    usuarios, headers, emails = {}, {}, {}
    for nome in ("criador", "convidado", "outro", "estranho"):
        email = email_teste.replace("@", f"-{nome}@")
        usuario = SQLAlchemyUsuarioRepository(db_session).salvar(
            Usuario(nome=nome, email=email, senha_hash="hash-de-teste")
        )
        usuarios[nome] = usuario.id
        emails[nome] = email
        token = get_token_service().gerar_token(usuario.id, usuario.versao_sessao)
        headers[nome] = {"Authorization": f"Bearer {token}"}
    viagem = CriarViagem(
        SQLAlchemyViagemRepository(db_session), SQLAlchemyUnitOfWork(db_session)
    ).execute(usuarios["criador"], "Floripa", None, date(2027, 1, 10), date(2027, 1, 20))
    db_session.commit()
    return {"usuarios": usuarios, "headers": headers, "emails": emails, "viagem": viagem.id}


def convidar(client, cenario, email_sender, quem="convidado", email=None) -> str:
    response = client.post(
        f"/viagens/{cenario['viagem']}/convites",
        json={"email": email or cenario["emails"][quem]},
        headers=cenario["headers"]["criador"],
    )
    assert response.status_code == 201, response.text
    link = next(
        linha for linha in email_sender.enviados[-1].corpo.splitlines()
        if linha.startswith(settings.CONVITE_URL)
    )
    return parse_qs(urlparse(link).query)["token"][0]


def aceitar(client, cenario, quem, token):
    return client.post(
        "/viagens/convites/aceitar", json={"token": token}, headers=cenario["headers"][quem]
    )


def test_fluxo_convite_email_promocao_rebaixamento_e_remocao(client, cenario, email_sender):
    viagem = f"/viagens/{cenario['viagem']}"
    convidado = cenario["headers"]["convidado"]
    convidado_id = cenario["usuarios"]["convidado"]
    alteracao = {"nome": "Floripa 2027"}

    assert client.get(viagem, headers=convidado).status_code == 404

    token = convidar(client, cenario, email_sender)
    assert email_sender.enviados[-1].destinatario == cenario["emails"]["convidado"]

    response = aceitar(client, cenario, "convidado", token)
    assert response.status_code == 201, response.text
    assert response.json()["id"] == cenario["viagem"]
    assert response.json()["papel_usuario"] == "visualizador"

    # Visualizador: consulta, mas não edita.
    assert client.get(viagem, headers=convidado).status_code == 200
    assert client.patch(viagem, json=alteracao, headers=convidado).status_code == 403

    # Promovido a editor: a próxima operação já pode editar.
    response = client.patch(
        f"{viagem}/membros/{convidado_id}",
        json={"papel": "editor"},
        headers=cenario["headers"]["criador"],
    )
    assert response.status_code == 200, response.text
    assert response.json()["papel"] == "editor"
    assert client.patch(viagem, json=alteracao, headers=convidado).status_code == 200

    # Rebaixado: volta a ser somente leitura.
    client.patch(
        f"{viagem}/membros/{convidado_id}",
        json={"papel": "visualizador"},
        headers=cenario["headers"]["criador"],
    )
    assert client.patch(viagem, json=alteracao, headers=convidado).status_code == 403

    # Removido: perde o acesso e a viagem some da lista dele.
    response = client.delete(
        f"{viagem}/membros/{convidado_id}", headers=cenario["headers"]["criador"]
    )
    assert response.status_code == 204
    assert client.get(viagem, headers=convidado).status_code == 404
    assert client.get("/viagens", headers=convidado).json()["itens"] == []
    # E o link já usado não devolve o acesso.
    assert aceitar(client, cenario, "convidado", token).status_code == 409


def test_aceite_repetido_retorna_409(client, cenario, email_sender, db_session):
    token = convidar(client, cenario, email_sender)
    assert aceitar(client, cenario, "convidado", token).status_code == 201

    response = aceitar(client, cenario, "convidado", token)

    assert response.status_code == 409
    vinculos = db_session.scalars(
        select(MembroViagemModel).where(
            MembroViagemModel.viagem_id == cenario["viagem"],
            MembroViagemModel.usuario_id == cenario["usuarios"]["convidado"],
        )
    ).all()
    assert len(vinculos) == 1


def test_link_encaminhado_para_outra_conta_retorna_403(client, cenario, email_sender):
    token = convidar(client, cenario, email_sender)

    response = aceitar(client, cenario, "estranho", token)

    assert response.status_code == 403
    assert client.get(
        f"/viagens/{cenario['viagem']}", headers=cenario["headers"]["estranho"]
    ).status_code == 404
    assert aceitar(client, cenario, "convidado", token).status_code == 201


def test_convidado_sem_conta_se_cadastra_e_aceita(client, cenario, email_sender, email_teste):
    email = email_teste.replace("@", "-novo@")
    token = convidar(client, cenario, email_sender, email=email)

    assert client.post(
        "/usuarios", json={"nome": "Nova", "email": email, "senha": "senha123"}
    ).status_code == 201
    login = client.post("/auth/login", json={"email": email, "senha": "senha123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.post("/viagens/convites/aceitar", json={"token": token}, headers=headers)

    assert response.status_code == 201, response.text
    assert response.json()["papel_usuario"] == "visualizador"


@pytest.mark.parametrize("token", ["inexistente", "x" * 43])
def test_token_inexistente_retorna_404(client, cenario, token):
    response = aceitar(client, cenario, "convidado", token)
    assert response.status_code == 404
    assert response.json() == {"detail": "Convite inválido ou expirado"}


def test_convite_expirado_retorna_404(client, cenario, email_sender, db_session):
    token = convidar(client, cenario, email_sender)
    db_session.execute(
        update(ConviteViagemModel)
        .where(ConviteViagemModel.viagem_id == cenario["viagem"])
        .values(expira_em=datetime.now(timezone.utc) - timedelta(seconds=1))
    )
    db_session.commit()

    response = aceitar(client, cenario, "convidado", token)

    assert response.status_code == 404
    assert response.json() == {"detail": "Convite inválido ou expirado"}


def test_aceite_nao_permite_escolher_papel_nem_viagem(client, cenario, email_sender):
    token = convidar(client, cenario, email_sender)
    for extra in ({"papel": "editor"}, {"viagem_id": cenario["viagem"]}):
        response = client.post(
            "/viagens/convites/aceitar",
            json={"token": token, **extra},
            headers=cenario["headers"]["convidado"],
        )
        assert response.status_code == 422


def test_nao_existe_ingresso_pelo_id_da_viagem(client, cenario):
    for rota in ("membros", "convites/aceitar", "entrar"):
        response = client.post(
            f"/viagens/{cenario['viagem']}/{rota}",
            json={},
            headers=cenario["headers"]["estranho"],
        )
        assert response.status_code in (404, 405)
    assert client.get(
        f"/viagens/{cenario['viagem']}", headers=cenario["headers"]["estranho"]
    ).status_code == 404


def test_nao_convida_quem_ja_participa(client, cenario, email_sender):
    response = client.post(
        f"/viagens/{cenario['viagem']}/convites",
        json={"email": cenario["emails"]["criador"]},
        headers=cenario["headers"]["criador"],
    )
    assert response.status_code == 409
    assert email_sender.enviados == []


def test_reenvio_invalida_link_anterior(client, cenario, email_sender):
    antigo = convidar(client, cenario, email_sender)
    novo = convidar(client, cenario, email_sender)

    assert aceitar(client, cenario, "convidado", antigo).status_code == 404
    assert aceitar(client, cenario, "convidado", novo).status_code == 201


def test_falha_no_envio_retorna_503_e_nao_grava(client, cenario, db_session):
    app.dependency_overrides[get_email_sender] = lambda: EmailSenderMemory(falhar=True)

    response = client.post(
        f"/viagens/{cenario['viagem']}/convites",
        json={"email": cenario["emails"]["convidado"]},
        headers=cenario["headers"]["criador"],
    )

    assert response.status_code == 503
    assert db_session.scalars(
        select(ConviteViagemModel).where(ConviteViagemModel.viagem_id == cenario["viagem"])
    ).all() == []


def test_criador_lista_e_cancela_convites(client, cenario, email_sender):
    base = f"/viagens/{cenario['viagem']}/convites"
    headers = cenario["headers"]["criador"]
    token = convidar(client, cenario, email_sender)

    pendentes = client.get(base, headers=headers).json()
    assert [c["email"] for c in pendentes] == [cenario["emails"]["convidado"].lower()]
    assert "token" not in pendentes[0] and "token_hash" not in pendentes[0]

    assert client.delete(f"{base}/{pendentes[0]['id']}", headers=headers).status_code == 204
    assert client.get(base, headers=headers).json() == []
    assert client.delete(f"{base}/{pendentes[0]['id']}", headers=headers).status_code == 404
    assert aceitar(client, cenario, "convidado", token).status_code == 404


def test_convites_e_gestao_sao_exclusivos_do_criador(client, cenario, email_sender):
    viagem = f"/viagens/{cenario['viagem']}"
    aceitar(client, cenario, "convidado", convidar(client, cenario, email_sender))
    aceitar(client, cenario, "outro", convidar(client, cenario, email_sender, "outro"))
    client.patch(
        f"{viagem}/membros/{cenario['usuarios']['convidado']}",
        json={"papel": "editor"},
        headers=cenario["headers"]["criador"],
    )

    for quem in ("convidado", "outro"):
        headers = cenario["headers"][quem]
        assert client.get(f"{viagem}/convites", headers=headers).status_code == 403
        assert client.post(
            f"{viagem}/convites", json={"email": "x@example.com"}, headers=headers
        ).status_code == 403
        for alvo in ("convidado", "outro"):
            membro = f"{viagem}/membros/{cenario['usuarios'][alvo]}"
            # Escalada de privilégio: nem o editor se promove ou promove outros.
            assert client.patch(
                membro, json={"papel": "editor"}, headers=headers
            ).status_code == 403
            assert client.delete(membro, headers=headers).status_code == 403

    headers = cenario["headers"]["estranho"]
    assert client.get(f"{viagem}/convites", headers=headers).status_code == 404
    assert client.get(f"{viagem}/membros", headers=headers).status_code == 404


def test_lista_membros_com_criador_primeiro(client, cenario, email_sender):
    aceitar(client, cenario, "convidado", convidar(client, cenario, email_sender))

    response = client.get(
        f"/viagens/{cenario['viagem']}/membros", headers=cenario["headers"]["convidado"]
    )

    assert response.status_code == 200
    assert [(m["usuario_id"], m["papel"]) for m in response.json()] == [
        (cenario["usuarios"]["criador"], "criador"),
        (cenario["usuarios"]["convidado"], "visualizador"),
    ]


def test_criador_nao_pode_ser_alterado_nem_removido(client, cenario):
    membro = f"/viagens/{cenario['viagem']}/membros/{cenario['usuarios']['criador']}"
    headers = cenario["headers"]["criador"]
    assert client.patch(membro, json={"papel": "visualizador"}, headers=headers).status_code == 400
    assert client.delete(membro, headers=headers).status_code == 400


@pytest.mark.parametrize("papel", ["criador", "admin"])
def test_papel_fora_do_enum_retorna_422(client, cenario, email_sender, papel):
    aceitar(client, cenario, "convidado", convidar(client, cenario, email_sender))
    response = client.patch(
        f"/viagens/{cenario['viagem']}/membros/{cenario['usuarios']['convidado']}",
        json={"papel": papel},
        headers=cenario["headers"]["criador"],
    )
    assert response.status_code == 422


def test_alvo_que_nao_e_membro_retorna_404(client, cenario):
    membro = f"/viagens/{cenario['viagem']}/membros/{cenario['usuarios']['estranho']}"
    headers = cenario["headers"]["criador"]
    assert client.patch(membro, json={"papel": "editor"}, headers=headers).status_code == 404
    assert client.delete(membro, headers=headers).status_code == 404


def test_sem_token_retorna_401(client, cenario):
    assert client.post("/viagens/convites/aceitar", json={"token": "X"}).status_code == 401
    assert client.get(f"/viagens/{cenario['viagem']}/membros").status_code == 401
    assert client.post(
        f"/viagens/{cenario['viagem']}/convites", json={"email": "x@example.com"}
    ).status_code == 401


def test_constraint_do_banco_barra_vinculo_duplicado(db_session, cenario):
    membros = SQLAlchemyMembroViagemRepository(db_session)
    membros.adicionar(cenario["viagem"], cenario["usuarios"]["convidado"], PapelMembro.EDITOR)

    with pytest.raises(MembroJaParticipa):
        membros.adicionar(
            cenario["viagem"], cenario["usuarios"]["convidado"], PapelMembro.VISUALIZADOR
        )
