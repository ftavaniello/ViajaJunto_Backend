from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.adapters.outbound.persistence.avaliacao_model import AvaliacaoModel
from app.adapters.outbound.persistence.catalogo_model import (
    CatalogoAtividadeModel,
    DestinoCatalogoModel,
)
from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.adapters.outbound.persistence.roteiro_model import AtividadeViagemModel, DestinoViagemModel
from app.adapters.outbound.persistence.unit_of_work_sqlalchemy import SQLAlchemyUnitOfWork
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.persistence.viagem_model import MembroViagemModel
from app.adapters.outbound.persistence.viagem_repository_sqlalchemy import (
    SQLAlchemyViagemRepository,
)
from app.application.use_cases.criar_viagem import CriarViagem
from app.domain.entities.catalogo import DestinoCatalogo
from app.domain.entities.usuario import Usuario
from app.infrastructure.database import get_db
from app.infrastructure.dependencies import get_gerenciar_destinos_viagem, get_token_service
from app.main import app


@pytest.fixture
def client(db_session):
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def cenario(db_session, email_teste):
    usuarios, headers = {}, {}
    for papel in ("criador", "editor", "visualizador", "estranho"):
        usuario = SQLAlchemyUsuarioRepository(db_session).salvar(
            Usuario(
                nome=papel,
                email=email_teste.replace("@", f"-{papel}@"),
                senha_hash="hash-de-teste",
            )
        )
        usuarios[papel] = usuario.id
        token = get_token_service().gerar_token(usuario.id, usuario.versao_sessao)
        headers[papel] = {"Authorization": f"Bearer {token}"}
    criar = CriarViagem(SQLAlchemyViagemRepository(db_session), SQLAlchemyUnitOfWork(db_session))
    viagens = [
        criar.execute(
            usuarios["criador"],
            nome,
            None,
            date(2027, 7, 1),
            date(2027, 7, 20),
        ).id
        for nome in ("Europa", "Outra viagem")
    ]
    for papel in ("editor", "visualizador"):
        db_session.add(
            MembroViagemModel(
                viagem_id=viagens[0],
                usuario_id=usuarios[papel],
                papel=papel,
            )
        )
    destino = SQLAlchemyCatalogoRepository(db_session).salvar_destino(
        DestinoCatalogo(
            nome="Lisboa",
            pais_codigo="PT",
            descricao="Descrição pública",
            categoria="cidade",
        )
    )
    db_session.commit()
    return {
        "usuarios": usuarios,
        "headers": headers,
        "viagem": viagens[0],
        "outra": viagens[1],
        "catalogo": destino.id,
    }


def adicionar(client, cenario, **campos):
    viagem = campos.pop("viagem", cenario["viagem"])
    response = client.post(
        f"/viagens/{viagem}/destinos",
        json={
            "destino_catalogo_id": cenario["catalogo"],
            "data_chegada": "2027-07-02",
            "data_saida": "2027-07-05",
            "descricao": "Particular",
            **campos,
        },
        headers=cenario["headers"]["criador"],
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("papel", ["criador", "editor", "visualizador"])
def test_participantes_leem_roteiro(client, cenario, papel):
    destino = adicionar(client, cenario)
    base = f"/viagens/{cenario['viagem']}/destinos"
    headers = cenario["headers"][papel]
    assert client.get(base, headers=headers).json() == [destino]
    assert client.get(f"{base}/{destino['id']}", headers=headers).json() == destino
    assert destino["destino"]["categoria"] == "cidade"
    assert destino["destino_catalogo_id"] == cenario["catalogo"]


@pytest.mark.parametrize("papel", ["criador", "editor"])
def test_fluxo_insercao_reordenacao_edicao_exclusao(client, cenario, papel, db_session):
    primeira = adicionar(client, cenario)
    segunda = adicionar(client, cenario, ordem=1)
    base = f"/viagens/{cenario['viagem']}/destinos"
    headers = cenario["headers"][papel]
    assert [d["id"] for d in client.get(base, headers=headers).json()] == [
        segunda["id"],
        primeira["id"],
    ]
    response = client.put(
        f"{base}/ordem", json={"destinos_ids": [primeira["id"], segunda["id"]]}, headers=headers
    )
    assert response.status_code == 200
    assert [d["ordem"] for d in response.json()] == [1, 2]
    # Força a validação real da unicidade adiada, mesmo dentro do SAVEPOINT do teste.
    db_session.execute(text("SET CONSTRAINTS uq_destinos_viagem_ordem IMMEDIATE"))
    db_session.execute(text("SET CONSTRAINTS uq_destinos_viagem_ordem DEFERRED"))
    response = client.patch(
        f"{base}/{primeira['id']}",
        json={
            "descricao": "Minha descrição",
            "hospedagem": "Hotel",
            "data_saida": "2027-07-06",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["destino"]["descricao"] == "Descrição pública"
    assert response.json()["descricao"] == "Minha descrição"
    assert (
        client.get(f"/catalogo/destinos/{cenario['catalogo']}").json()["descricao"]
        == "Descrição pública"
    )
    assert client.delete(f"{base}/{primeira['id']}", headers=headers).status_code == 204
    restantes = client.get(base, headers=headers).json()
    assert [(d["id"], d["ordem"]) for d in restantes] == [(segunda["id"], 1)]


@pytest.mark.parametrize(
    "metodo,sufixo,body",
    [
        ("get", "", None),
        ("get", "/1", None),
        (
            "post",
            "",
            {"destino_catalogo_id": 1, "data_chegada": "2027-07-02", "data_saida": "2027-07-05"},
        ),
        ("patch", "/1", {}),
        ("delete", "/1", None),
        ("put", "/ordem", {"destinos_ids": []}),
    ],
)
def test_rotas_destinos_exigem_token(client, metodo, sufixo, body):
    kwargs = {"json": body} if body is not None else {}
    assert getattr(client, metodo)(f"/viagens/1/destinos{sufixo}", **kwargs).status_code == 401


@pytest.mark.parametrize("papel,status", [("visualizador", 403), ("estranho", 404)])
@pytest.mark.parametrize("metodo", ["post", "patch", "delete", "put"])
def test_permissoes_de_escrita(client, cenario, papel, status, metodo):
    destino = adicionar(client, cenario)
    base = f"/viagens/{cenario['viagem']}/destinos"
    destinos_ids = [destino["id"]]
    rota = (
        base
        if metodo == "post"
        else f"{base}/ordem"
        if metodo == "put"
        else f"{base}/{destino['id']}"
    )
    corpo = (
        {"destinos_ids": destinos_ids}
        if metodo == "put"
        else {
            "destino_catalogo_id": cenario["catalogo"],
            "data_chegada": "2027-07-02",
            "data_saida": "2027-07-05",
        }
        if metodo == "post"
        else {"descricao": "Alterada"}
    )
    kwargs = {} if metodo == "delete" else {"json": corpo}
    response = getattr(client, metodo)(rota, headers=cenario["headers"][papel], **kwargs)
    assert response.status_code == status
    assert client.get(base, headers=cenario["headers"]["criador"]).json() == [destino]


@pytest.mark.parametrize("metodo", ["get", "patch", "delete"])
def test_id_destino_de_outra_viagem_nao_pode_ser_usado(client, cenario, metodo):
    destino = adicionar(client, cenario, viagem=cenario["outra"])
    rota = f"/viagens/{cenario['viagem']}/destinos/{destino['id']}"
    kwargs = {"json": {"descricao": "Invasão"}} if metodo == "patch" else {}
    response = getattr(client, metodo)(rota, headers=cenario["headers"]["criador"], **kwargs)
    assert response.status_code == 404


@pytest.mark.parametrize("ids", [[], [1, 1], [99999999]])
def test_reordenacao_incompleta_duplicada_ou_alheia(client, cenario, ids):
    destino = adicionar(client, cenario)
    base = f"/viagens/{cenario['viagem']}/destinos"
    if ids == [1, 1]:
        ids = [destino["id"], destino["id"]]
    response = client.put(
        f"{base}/ordem", json={"destinos_ids": ids}, headers=cenario["headers"]["criador"]
    )
    assert response.status_code == 400
    assert client.get(base, headers=cenario["headers"]["criador"]).json() == [destino]


@pytest.mark.parametrize(
    "campos,status",
    [
        ({"data_saida": "2027-07-01"}, 400),
        ({"data_chegada": "2027-06-30"}, 400),
        ({"data_saida": "2027-07-21"}, 400),
        ({"ordem": 2}, 400),
        ({"ordem": 0}, 422),
        ({"destino_catalogo_id": 999999999}, 404),
        ({"criador_id": 999}, 422),
    ],
)
def test_criacao_invalida_nao_grava(client, cenario, campos, status):
    base = f"/viagens/{cenario['viagem']}/destinos"
    response = client.post(
        base,
        json={
            "destino_catalogo_id": cenario["catalogo"],
            "data_chegada": "2027-07-02",
            "data_saida": "2027-07-05",
            **campos,
        },
        headers=cenario["headers"]["criador"],
    )
    assert response.status_code == status
    assert client.get(base, headers=cenario["headers"]["criador"]).json() == []


def test_encolher_viagem_e_parada_preserva_datas_das_atividades(client, cenario, db_session):
    destino = adicionar(client, cenario)
    atividade = CatalogoAtividadeModel(
        destino_catalogo_id=cenario["catalogo"], nome="Museu", categoria="cultura"
    )
    db_session.add(atividade)
    db_session.flush()
    db_session.add(
        AtividadeViagemModel(
            destino_viagem_id=destino["id"],
            catalogo_atividade_id=atividade.id,
            data=date(2027, 7, 3),
        )
    )
    db_session.commit()
    headers = cenario["headers"]["criador"]
    base = f"/viagens/{cenario['viagem']}"
    assert client.patch(base, json={"data_fim": "2027-07-04"}, headers=headers).status_code == 400
    assert client.get(base, headers=headers).json()["data_fim"] == "2027-07-20"
    assert (
        client.patch(
            f"{base}/destinos/{destino['id']}", json={"data_chegada": "2027-07-04"}, headers=headers
        ).status_code
        == 400
    )
    assert client.get(f"{base}/destinos/{destino['id']}", headers=headers).json() == destino


def test_exclusao_cascata_preserva_catalogo_e_avaliacao(client, cenario, db_session):
    primeira = adicionar(client, cenario)
    segunda = adicionar(client, cenario)
    atividade = CatalogoAtividadeModel(
        destino_catalogo_id=cenario["catalogo"], nome="Museu", categoria="cultura"
    )
    db_session.add(atividade)
    db_session.flush()
    planejada = AtividadeViagemModel(
        destino_viagem_id=primeira["id"], catalogo_atividade_id=atividade.id, data=date(2027, 7, 3)
    )
    db_session.add(planejada)
    db_session.flush()
    avaliacao = AvaliacaoModel(
        usuario_id=cenario["usuarios"]["criador"],
        catalogo_atividade_id=atividade.id,
        atividade_viagem_id=planejada.id,
        nota=5,
    )
    db_session.add(avaliacao)
    db_session.commit()
    planejada_id, atividade_id, avaliacao_id = planejada.id, atividade.id, avaliacao.id
    base = f"/viagens/{cenario['viagem']}/destinos"
    headers = cenario["headers"]["criador"]
    assert client.delete(f"{base}/{primeira['id']}", headers=headers).status_code == 204
    db_session.expire_all()
    assert db_session.get(AtividadeViagemModel, planejada_id) is None
    assert db_session.get(DestinoViagemModel, primeira["id"]) is None
    assert db_session.get(CatalogoAtividadeModel, atividade_id) is not None
    assert db_session.get(DestinoCatalogoModel, cenario["catalogo"]) is not None
    assert db_session.get(AvaliacaoModel, avaliacao_id).atividade_viagem_id is None
    assert [(d["id"], d["ordem"]) for d in client.get(base, headers=headers).json()] == [
        (segunda["id"], 1)
    ]


def test_falha_na_reordenacao_reverte_todas_posicoes(client, cenario, db_session, monkeypatch):
    primeira = adicionar(client, cenario)
    segunda = adicionar(client, cenario)
    caso = get_gerenciar_destinos_viagem(db_session)
    original = caso.repository.salvar
    chamadas = 0

    def falhar_no_segundo(destino):
        nonlocal chamadas
        chamadas += 1
        if chamadas == 2:
            raise RuntimeError("falha simulada")
        return original(destino)

    monkeypatch.setattr(caso.repository, "salvar", falhar_no_segundo)
    app.dependency_overrides[get_gerenciar_destinos_viagem] = lambda: caso
    base = f"/viagens/{cenario['viagem']}/destinos"
    headers = cenario["headers"]["criador"]
    corpo = {"destinos_ids": [segunda["id"], primeira["id"]]}
    with pytest.raises(RuntimeError):
        client.put(f"{base}/ordem", json=corpo, headers=headers)
    assert client.get(base, headers=headers).json() == [primeira, segunda]


def test_remocao_de_membro_reflete_na_proxima_operacao(client, cenario, db_session):
    adicionar(client, cenario)
    membro = db_session.scalar(
        select(MembroViagemModel).where(
            MembroViagemModel.viagem_id == cenario["viagem"],
            MembroViagemModel.usuario_id == cenario["usuarios"]["editor"],
        )
    )
    db_session.delete(membro)
    db_session.commit()
    response = client.get(
        f"/viagens/{cenario['viagem']}/destinos", headers=cenario["headers"]["editor"]
    )
    assert response.status_code == 404


def test_openapi_roteiro_exige_autenticacao():
    contrato = app.openapi()
    for rota, operacoes in contrato["paths"].items():
        if rota.startswith("/viagens/{viagem_id}/destinos"):
            for operacao in operacoes.values():
                assert operacao.get("security")


def test_estranho_nao_lista_e_roteiro_vazio(client, cenario):
    base = f"/viagens/{cenario['viagem']}/destinos"
    assert client.get(base, headers=cenario["headers"]["estranho"]).status_code == 404
    assert client.get(base, headers=cenario["headers"]["criador"]).json() == []
    response = client.put(
        f"{base}/ordem", json={"destinos_ids": []}, headers=cenario["headers"]["criador"]
    )
    assert response.status_code == 200
    assert response.json() == []


def test_reordenacao_com_id_real_de_outra_viagem(client, cenario):
    propria = adicionar(client, cenario)
    alheia = adicionar(client, cenario, viagem=cenario["outra"])
    base = f"/viagens/{cenario['viagem']}/destinos"
    headers = cenario["headers"]["criador"]
    response = client.put(f"{base}/ordem", json={"destinos_ids": [alheia["id"]]}, headers=headers)
    assert response.status_code == 400
    assert client.get(base, headers=headers).json() == [propria]


def test_patch_omitido_nulo_e_vazio(client, cenario):
    destino = adicionar(client, cenario, hospedagem="Hotel")
    rota = f"/viagens/{cenario['viagem']}/destinos/{destino['id']}"
    headers = cenario["headers"]["criador"]
    response = client.patch(rota, json={"descricao": None}, headers=headers)
    assert response.status_code == 200
    assert response.json() == destino
    response = client.patch(rota, json={"descricao": "", "hospedagem": ""}, headers=headers)
    assert response.status_code == 200
    assert response.json()["descricao"] is None
    assert response.json()["hospedagem"] is None
