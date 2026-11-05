from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.adapters.outbound.persistence.avaliacao_model import AvaliacaoModel
from app.adapters.outbound.persistence.catalogo_model import (
    CatalogoAtividadeModel,
    DestinoCatalogoModel,
)
from app.adapters.outbound.persistence.roteiro_model import AtividadeViagemModel
from app.adapters.outbound.persistence.seed_demonstracao_repository_sqlalchemy import (
    SeedDemonstracaoModel,
    SQLAlchemySeedDemonstracaoRepository,
)
from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.adapters.outbound.persistence.viagem_model import ViagemModel
from app.application.use_cases.semear_demonstracao import EMAILS_SEED, SENHA_SEED
from app.domain.errors import DadosInvalidos
from app.infrastructure.config import carregar_settings
from app.infrastructure.database import get_db
from app.infrastructure.dependencies import get_gerenciar_orcamento_viagem
from app.infrastructure.seed_demonstracao import executar_seed_completo
from app.main import app

CONFIG = carregar_settings({"APP_ENV": "development"})
REFERENCIA = date(2027, 1, 15)


@pytest.fixture
def cenario_seed(db_session):
    criado, manifesto = executar_seed_completo(CONFIG, db_session.connection(), REFERENCIA)
    assert criado
    return manifesto


@pytest.fixture
def client(db_session):
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def login(client, papel):
    resposta = client.post("/auth/login", json={"email": EMAILS_SEED[papel], "senha": SENHA_SEED})
    assert resposta.status_code == 200, resposta.text
    return {"Authorization": "Bearer " + resposta.json()["access_token"]}


def test_seed_tem_apenas_destinos_reais_e_nomes_sem_prefixos(client, db_session, cenario_seed):
    m = cenario_seed
    for chave, total in [
        ("usuarios", 6),
        ("viagens", 28),
        ("destinos_catalogo", 4),
        ("atividades_catalogo", 24),
        ("paradas", 6),
        ("atividades_roteiro", 35),
        ("avaliacoes", 20),
    ]:
        assert len(m[chave]) == total
    assert db_session.scalar(select(func.count()).select_from(SeedDemonstracaoModel)) == 1
    assert db_session.scalar(select(func.count()).select_from(AvaliacaoModel)) == 20
    destinos = client.get("/catalogo/destinos").json()["itens"]
    assert {d["nome"] for d in destinos} == {"Orlando", "Miami", "Rio de Janeiro", "Roma"}
    for model, campo in [
        (UsuarioModel, UsuarioModel.nome),
        (ViagemModel, ViagemModel.nome),
        (DestinoCatalogoModel, DestinoCatalogoModel.nome),
        (CatalogoAtividadeModel, CatalogoAtividadeModel.nome),
    ]:
        assert all("demo" not in nome.lower() for nome in db_session.scalars(select(campo)))
    assert all(not c.startswith("[") for c in db_session.scalars(select(AvaliacaoModel.comentario)))
    for papel in EMAILS_SEED:
        assert client.get("/usuarios/me", headers=login(client, papel)).status_code == 200


def test_listas_e_paginacao(client, cenario_seed):
    headers = login(client, "criador")
    pagina1 = client.get("/viagens", headers=headers).json()
    pagina2 = client.get("/viagens?pagina=2", headers=headers).json()
    assert len(pagina1["itens"]) == 20 and pagina1["tem_proxima"]
    assert len(pagina2["itens"]) == 6 and not pagina2["tem_proxima"]
    for papel, total in [
        ("editor", 2),
        ("visualizador", 2),
        ("externo", 1),
        ("vazio", 0),
        ("descartavel", 1),
    ]:
        assert len(client.get("/viagens", headers=login(client, papel)).json()["itens"]) == total
    atividades = client.get("/catalogo/atividades").json()
    assert len(atividades["itens"]) == 20 and atividades["tem_proxima"]
    assert len(client.get("/catalogo/atividades?pagina=2").json()["itens"]) == 4
    assert len(client.get("/catalogo/destinos?pais_codigo=US").json()["itens"]) == 2


@pytest.mark.parametrize(
    "papel,status", [("criador", 200), ("editor", 200), ("visualizador", 403), ("externo", 404)]
)
def test_permissoes_de_edicao(client, cenario_seed, papel, status):
    m = cenario_seed
    caminho = (
        f"/viagens/{m['viagens']['florida']}/destinos/{m['paradas']['florida-orlando']}"
        f"/atividades/{m['atividades_roteiro']['florida-orlando-2']}"
    )
    headers = login(client, papel)
    assert (
        client.patch(caminho, headers=headers, json={"custo_previsto": "50.00"}).status_code
        == status
    )


def test_reviews_e_orcamentos(client, db_session, cenario_seed):
    m = cenario_seed
    for cidade in ("orlando", "miami", "rio", "roma"):
        detalhe = client.get(
            f"/catalogo/atividades/{m['atividades_catalogo'][cidade + '-1']}"
        ).json()
        assert detalhe["total_avaliacoes"] >= 1
        assert detalhe["reviews"]
    caso = get_gerenciar_orcamento_viagem(db_session)
    florida = caso.consultar_resumo(m["viagens"]["florida"], m["usuarios"]["criador"])
    privada = caso.consultar_resumo(m["viagens"]["roma-privada"], m["usuarios"]["externo"])
    assert florida.orcamento_total == 6000 and not florida.orcamento_excedido
    assert privada.orcamento_total == 500 and privada.orcamento_excedido


def test_reexecutar_preserva_edicoes_e_exclusoes(db_session, cenario_seed):
    m = cenario_seed
    usuario = db_session.get(UsuarioModel, m["usuarios"]["criador"])
    usuario.nome, usuario.senha_hash = "Nome editado", "hash-alterado"
    db_session.delete(db_session.get(ViagemModel, m["viagens"]["paginacao-01"]))
    db_session.flush()
    criado, mesmo = executar_seed_completo(CONFIG, db_session.connection(), date(2030, 1, 1))
    assert not criado and mesmo == m
    db_session.expire_all()
    assert usuario.nome == "Nome editado" and usuario.senha_hash == "hash-alterado"
    assert db_session.get(ViagemModel, m["viagens"]["paginacao-01"]) is None
    assert db_session.scalar(select(func.count()).select_from(CatalogoAtividadeModel)) == 24


def test_falha_no_final_desfaz_toda_carga(db_session, monkeypatch):
    models = (
        UsuarioModel,
        ViagemModel,
        CatalogoAtividadeModel,
        DestinoCatalogoModel,
        AvaliacaoModel,
        AtividadeViagemModel,
        SeedDemonstracaoModel,
    )
    antes = {model: db_session.scalar(select(func.count()).select_from(model)) for model in models}

    def falhar(*args):
        raise RuntimeError("Falha no final")

    monkeypatch.setattr(SQLAlchemySeedDemonstracaoRepository, "concluir", falhar)
    with pytest.raises(RuntimeError, match="Falha no final"):
        executar_seed_completo(CONFIG, db_session.connection(), REFERENCIA)
    for model in models:
        assert db_session.scalar(select(func.count()).select_from(model)) == antes[model]


@pytest.mark.parametrize("ambiente", ["production", "staging", "test"])
def test_bloqueio_antes_de_acessar_banco(ambiente):
    with pytest.raises(PermissionError):
        executar_seed_completo(carregar_settings({"APP_ENV": ambiente}), None, REFERENCIA)


def test_conta_existente_nao_e_apropriada_ou_apagada(db_session):
    usuario = UsuarioModel(
        nome="Pessoa existente", email=EMAILS_SEED["editor"], senha_hash="original"
    )
    db_session.add(usuario)
    db_session.flush()
    with pytest.raises(DadosInvalidos, match="Email reservado"):
        executar_seed_completo(CONFIG, db_session.connection(), REFERENCIA)
    assert usuario.senha_hash == "original"
    assert db_session.scalar(select(func.count()).select_from(ViagemModel)) == 0


def test_exclusao_da_conta_descartavel_preserva_reviews_publicos(client, db_session, cenario_seed):
    m = cenario_seed
    headers = login(client, "descartavel")
    assert client.delete("/usuarios/me", headers=headers).status_code == 204
    assert client.get("/usuarios/me", headers=headers).status_code == 401
    assert db_session.scalar(select(func.count()).select_from(AvaliacaoModel)) == 20
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(AvaliacaoModel)
            .where(AvaliacaoModel.usuario_id.is_(None))
        )
        == 2
    )
    assert db_session.get(ViagemModel, m["viagens"]["descartavel"]) is None


def test_conta_descartavel_permite_troca_senha_e_logout(client, cenario_seed):
    headers = login(client, "descartavel")
    assert (
        client.patch(
            "/usuarios/me/senha",
            headers=headers,
            json={
                "senha_atual": SENHA_SEED,
                "senha_nova": "OutraSenha123!",
            },
        ).status_code
        == 204
    )
    assert client.get("/usuarios/me", headers=headers).status_code == 401
    resposta = client.post(
        "/auth/login", json={"email": EMAILS_SEED["descartavel"], "senha": "OutraSenha123!"}
    )
    headers = {"Authorization": "Bearer " + resposta.json()["access_token"]}
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/usuarios/me", headers=headers).status_code == 401


def test_lock_permanece_ate_commit_externo(db_session, cenario_seed):
    from sqlalchemy import text

    from app.infrastructure.database import engine

    with engine.connect() as outra:
        assert outra.scalar(text("SELECT pg_try_advisory_xact_lock(202647, 1)")) is False


def test_ana_tem_tres_papeis_e_disney_springs_disponivel_para_demo(client, cenario_seed):
    m = cenario_seed
    headers = login(client, "criador")
    viagens = client.get("/viagens?tamanho_pagina=100", headers=headers).json()["itens"]
    assert {v["papel_usuario"] for v in viagens} == {"criador", "editor", "visualizador"}
    caminho = (
        f"/viagens/{m['viagens']['florida']}/destinos/{m['paradas']['florida-orlando']}/atividades"
    )
    disney = m["atividades_catalogo"]["orlando-3"]
    antes = client.get(caminho, headers=headers).json()
    assert all(a["catalogo_atividade_id"] != disney for a in antes)
    resposta = client.post(
        caminho,
        headers=headers,
        json={
            "catalogo_atividade_id": disney,
            "data": "2027-02-16",
            "hora_inicio": "10:00:00",
            "custo_previsto": "150.00",
        },
    )
    assert resposta.status_code == 201, resposta.text
    depois = client.get(caminho, headers=headers).json()
    assert sum(a["catalogo_atividade_id"] == disney for a in depois) == 1
