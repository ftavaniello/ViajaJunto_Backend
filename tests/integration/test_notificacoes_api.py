"""Notificações in-app (RF21) de ponta a ponta: API, PostgreSQL e transação."""
import importlib.util
import uuid
from datetime import date
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateSchema

from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.adapters.outbound.persistence.destino_viagem_repository_sqlalchemy import (
    SQLAlchemyDestinoViagemRepository,
)
from app.adapters.outbound.persistence.notificacao_model import NotificacaoModel
from app.adapters.outbound.persistence.unit_of_work_sqlalchemy import SQLAlchemyUnitOfWork
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.persistence.viagem_model import MembroViagemModel
from app.adapters.outbound.persistence.viagem_repository_sqlalchemy import (
    SQLAlchemyViagemRepository,
)
from app.application.use_cases.criar_viagem import CriarViagem
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.entities.usuario import Usuario
from app.infrastructure import dependencies
from app.infrastructure.database import get_db
from app.infrastructure.dependencies import get_token_service
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
    """Viagem "Europa" com editor e visualizador, uma parada em Lisboa e uma atividade."""
    usuarios, headers = {}, {}
    for papel, nome in (
        ("criador", "Ana"),
        ("editor", "Bruno"),
        ("visualizador", "Carla"),
        ("estranho", "Diego"),
    ):
        usuario = SQLAlchemyUsuarioRepository(db_session).salvar(
            Usuario(nome=nome, email=email_teste.replace("@", f"-{papel}@"), senha_hash="hash")
        )
        usuarios[papel] = usuario.id
        token = get_token_service().gerar_token(usuario.id, usuario.versao_sessao)
        headers[papel] = {"Authorization": f"Bearer {token}"}
    viagem = CriarViagem(
        SQLAlchemyViagemRepository(db_session), SQLAlchemyUnitOfWork(db_session)
    ).execute(usuarios["criador"], "Europa", None, date(2027, 7, 1), date(2027, 7, 20))
    for papel in ("editor", "visualizador"):
        db_session.add(
            MembroViagemModel(viagem_id=viagem.id, usuario_id=usuarios[papel], papel=papel)
        )
    catalogo = SQLAlchemyCatalogoRepository(db_session)
    lisboa = catalogo.salvar_destino(DestinoCatalogo(nome="Lisboa", pais_codigo="PT"))
    museu = catalogo.salvar_atividade(
        AtividadeCatalogo(destino=lisboa, nome="Museu", categoria="passeio")
    )
    parada = SQLAlchemyDestinoViagemRepository(db_session).salvar(
        DestinoViagem(
            viagem_id=viagem.id,
            destino=lisboa,
            ordem=1,
            data_chegada=date(2027, 7, 2),
            data_saida=date(2027, 7, 5),
        )
    )
    db_session.commit()
    return {
        "viagem": viagem.id,
        "parada": parada.id,
        "catalogo": museu.id,
        "usuarios": usuarios,
        "headers": headers,
        "atividades": f"/viagens/{viagem.id}/destinos/{parada.id}/atividades",
    }


def _adicionar_atividade(client, cenario, papel="criador"):
    response = client.post(
        cenario["atividades"],
        json={"catalogo_atividade_id": cenario["catalogo"], "data": "2027-07-03"},
        headers=cenario["headers"][papel],
    )
    assert response.status_code == 201, response.text
    return response.json()


def _notificacoes(client, cenario, papel, **params):
    response = client.get("/notificacoes", params=params, headers=cenario["headers"][papel])
    assert response.status_code == 200, response.text
    return response.json()


def _total_no_banco(db_session) -> int:
    return db_session.scalar(select(func.count()).select_from(NotificacaoModel))


def test_mudar_data_de_atividade_avisa_os_demais_que_consultam_e_marcam_como_lida(
    client, cenario
):
    atividade = _adicionar_atividade(client, cenario)
    client.post("/notificacoes/marcar-todas-lidas", headers=cenario["headers"]["editor"])

    response = client.patch(
        f"{cenario['atividades']}/{atividade['id']}",
        json={"data": "2027-07-04"},
        headers=cenario["headers"]["editor"],
    )
    assert response.status_code == 200

    caixa = _notificacoes(client, cenario, "criador")
    assert caixa["nao_lidas"] == 1
    aviso = caixa["itens"][0]
    assert aviso["tipo"] == "atividade_alterada"
    assert aviso["mensagem"] == (
        'Bruno alterou a data da atividade "Museu" em Lisboa (04/07/2027) na viagem "Europa".'
    )
    assert aviso["viagem_id"] == cenario["viagem"]
    assert aviso["ator_id"] == cenario["usuarios"]["editor"]
    assert aviso["lida"] is False and aviso["lida_em"] is None

    visualizador = _notificacoes(client, cenario, "visualizador")
    assert [n["tipo"] for n in visualizador["itens"]] == ["atividade_alterada"] * 2
    assert _notificacoes(client, cenario, "editor", nao_lidas=True)["itens"] == []
    assert _notificacoes(client, cenario, "estranho")["itens"] == []

    lida = client.patch(
        f"/notificacoes/{aviso['id']}/lida", headers=cenario["headers"]["criador"]
    )
    assert lida.status_code == 200
    assert lida.json()["lida"] is True and lida.json()["lida_em"] is not None
    contagem = client.get(
        "/notificacoes/nao-lidas/contagem", headers=cenario["headers"]["criador"]
    )
    assert contagem.json() == {"nao_lidas": 0}
    # A leitura de um não muda a caixa dos outros.
    assert _notificacoes(client, cenario, "visualizador")["nao_lidas"] == 2


def test_listagem_ordena_nao_lidas_primeiro_e_pagina(client, cenario):
    for _ in range(3):
        _adicionar_atividade(client, cenario, papel="editor")
    ids = [n["id"] for n in _notificacoes(client, cenario, "criador")["itens"]]
    assert ids == sorted(ids, reverse=True)  # mais recentes antes

    client.patch(f"/notificacoes/{ids[0]}/lida", headers=cenario["headers"]["criador"])

    assert [n["id"] for n in _notificacoes(client, cenario, "criador")["itens"]] == [
        ids[1],
        ids[2],
        ids[0],
    ]
    pagina = _notificacoes(client, cenario, "criador", pagina=1, tamanho_pagina=2)
    assert len(pagina["itens"]) == 2 and pagina["tem_proxima"] is True
    assert len(_notificacoes(client, cenario, "criador", nao_lidas=True)["itens"]) == 2


def test_usuario_nao_le_nem_altera_notificacao_alheia(client, cenario, db_session):
    _adicionar_atividade(client, cenario)
    alheia = _notificacoes(client, cenario, "editor")["itens"][0]

    for papel in ("estranho", "criador", "visualizador"):
        response = client.patch(
            f"/notificacoes/{alheia['id']}/lida", headers=cenario["headers"][papel]
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Notificação não encontrada"}
    inexistente = client.patch("/notificacoes/999999999/lida", headers=cenario["headers"]["editor"])
    assert inexistente.status_code == 404

    marcadas = client.post(
        "/notificacoes/marcar-todas-lidas", headers=cenario["headers"]["estranho"]
    )
    assert marcadas.json() == {"marcadas": 0}
    assert db_session.get(NotificacaoModel, alheia["id"]).lida_em is None
    assert _notificacoes(client, cenario, "editor")["nao_lidas"] == 1


def test_marcar_todas_lidas(client, cenario):
    _adicionar_atividade(client, cenario)
    _adicionar_atividade(client, cenario)

    response = client.post(
        "/notificacoes/marcar-todas-lidas", headers=cenario["headers"]["editor"]
    )

    assert response.json() == {"marcadas": 2}
    assert _notificacoes(client, cenario, "editor")["nao_lidas"] == 0
    assert _notificacoes(client, cenario, "visualizador")["nao_lidas"] == 2


@pytest.mark.parametrize(
    ("metodo", "rota"),
    [
        ("get", "/notificacoes"),
        ("get", "/notificacoes/nao-lidas/contagem"),
        ("patch", "/notificacoes/1/lida"),
        ("post", "/notificacoes/marcar-todas-lidas"),
    ],
)
def test_notificacoes_exigem_token(client, metodo, rota):
    assert getattr(client, metodo)(rota).status_code == 401


@pytest.mark.parametrize(
    "params", [{"pagina": 0}, {"tamanho_pagina": 0}, {"tamanho_pagina": 101}]
)
def test_paginacao_invalida(client, cenario, params):
    response = client.get("/notificacoes", params=params, headers=cenario["headers"]["criador"])
    assert response.status_code == 422


# --- Somente alterações confirmadas -----------------------------------------------


def test_requisicao_recusada_nao_gera_aviso(client, cenario, db_session):
    atividade = _adicionar_atividade(client, cenario)
    antes = _total_no_banco(db_session)
    rota = f"{cenario['atividades']}/{atividade['id']}"

    fora_da_parada = client.patch(
        rota, json={"data": "2027-07-19"}, headers=cenario["headers"]["editor"]
    )
    sem_permissao = client.patch(
        rota, json={"data": "2027-07-04"}, headers=cenario["headers"]["visualizador"]
    )

    assert (fora_da_parada.status_code, sem_permissao.status_code) == (400, 403)
    assert _total_no_banco(db_session) == antes


def test_rollback_da_operacao_desfaz_o_aviso_ja_gravado(cenario, db_session):
    """O aviso chega ao banco (flush) e a falha no commit desfaz alteração e aviso juntos."""

    class CommitFalho(SQLAlchemyUnitOfWork):
        def commit(self):
            raise RuntimeError("falha ao confirmar")

    caso = dependencies.get_gerenciar_atividades_viagem(db_session)
    caso.uow = CommitFalho(db_session)

    with pytest.raises(RuntimeError):
        caso.criar(
            cenario["viagem"],
            cenario["parada"],
            cenario["usuarios"]["editor"],
            cenario["catalogo"],
            date(2027, 7, 3),
        )

    assert _total_no_banco(db_session) == 0
    assert caso.repository.listar(cenario["viagem"], cenario["parada"]) == []


# --- Outros eventos ---------------------------------------------------------------


def test_viagem_excluida_avisa_colaboradores_e_aviso_sobrevive(client, cenario):
    response = client.delete(
        f"/viagens/{cenario['viagem']}", headers=cenario["headers"]["criador"]
    )
    assert response.status_code == 204

    for papel in ("editor", "visualizador"):
        aviso = _notificacoes(client, cenario, papel)["itens"][0]
        assert aviso["tipo"] == "viagem_excluida"
        assert aviso["viagem_id"] is None
        assert aviso["mensagem"] == 'Ana excluiu a viagem "Europa" (01/07/2027 a 20/07/2027).'
        lida = client.patch(f"/notificacoes/{aviso['id']}/lida", headers=cenario["headers"][papel])
        assert lida.status_code == 200
    assert _notificacoes(client, cenario, "criador")["itens"] == []


def test_alterar_papel_e_remover_membro_avisam_o_afetado(client, cenario):
    base = f"/viagens/{cenario['viagem']}/membros"
    headers = cenario["headers"]["criador"]

    client.patch(
        f"{base}/{cenario['usuarios']['visualizador']}", json={"papel": "editor"}, headers=headers
    )
    client.delete(f"{base}/{cenario['usuarios']['editor']}", headers=headers)

    assert [n["tipo"] for n in _notificacoes(client, cenario, "visualizador")["itens"]] == [
        "papel_alterado"
    ]
    removido = _notificacoes(client, cenario, "editor")["itens"]
    assert [n["mensagem"] for n in removido] == ['Ana removeu você da viagem "Europa".']
    # O removido mantém o histórico, mas não recebe avisos novos.
    _adicionar_atividade(client, cenario)
    assert len(_notificacoes(client, cenario, "editor")["itens"]) == 1


def test_atualizar_viagem_e_roteiro_avisam(client, cenario):
    headers = cenario["headers"]["editor"]
    client.patch(f"/viagens/{cenario['viagem']}", json={"status": "confirmada"}, headers=headers)
    client.patch(
        f"/viagens/{cenario['viagem']}/destinos/{cenario['parada']}",
        json={"data_saida": "2027-07-06"},
        headers=headers,
    )

    tipos = [n["tipo"] for n in _notificacoes(client, cenario, "criador")["itens"]]
    assert tipos == ["roteiro_alterado", "viagem_alterada"]


def test_conta_do_ator_excluida_mantem_aviso_sem_ator(client, cenario, db_session):
    _adicionar_atividade(client, cenario, papel="editor")

    assert client.delete("/usuarios/me", headers=cenario["headers"]["editor"]).status_code == 204

    aviso = _notificacoes(client, cenario, "criador")["itens"][0]
    assert aviso["ator_id"] is None
    assert aviso["mensagem"].startswith("Bruno adicionou")


# --- Migração ---------------------------------------------------------------------


def test_banco_aceita_somente_os_tipos_do_dominio(cenario, db_session):
    db_session.add(
        NotificacaoModel(
            usuario_id=cenario["usuarios"]["criador"], tipo="roteiro_alterado", mensagem="ok"
        )
    )
    db_session.flush()
    db_session.add(
        NotificacaoModel(usuario_id=cenario["usuarios"]["criador"], tipo="outro", mensagem="x")
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_migracao_dos_tipos_sobe_e_desce(db_session):
    schema = "tipos_notificacao_" + uuid.uuid4().hex
    db_session.execute(CreateSchema(schema))
    db_session.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    db_session.execute(
        text(
            "CREATE TABLE notificacoes (id INTEGER PRIMARY KEY, tipo VARCHAR(30) NOT NULL, "
            "CONSTRAINT ck_notificacoes_tipo CHECK (tipo IN ('membro_entrou', "
            "'papel_alterado', 'membro_removido', 'viagem_excluida')))"
        )
    )
    db_session.execute(text("INSERT INTO notificacoes VALUES (1, 'membro_entrou')"))
    arquivo = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/e9c4b7a15d28_tipos_notificacao_rf21.py"
    )
    spec = importlib.util.spec_from_file_location("migracao_tipos_notificacao", arquivo)
    migracao = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migracao)

    with Operations.context(MigrationContext.configure(db_session.connection())):
        migracao.upgrade()
        db_session.execute(text("INSERT INTO notificacoes VALUES (2, 'atividade_alterada')"))
        migracao.downgrade()

    tipos = list(db_session.scalars(text("SELECT tipo FROM notificacoes ORDER BY id")))
    assert tipos == ["membro_entrou"]
