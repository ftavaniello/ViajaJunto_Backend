from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

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
from app.infrastructure.config import carregar_settings
from app.infrastructure.database import get_db
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


def test_seed_completo_cobre_cenarios_e_login(client, db_session, cenario_seed):
    m = cenario_seed
    assert len(m["usuarios"]) == 6
    assert len(m["viagens"]) == 26
    assert len(m["destinos_catalogo"]) == 24
    assert len(m["atividades_catalogo"]) == 144
    assert len(m["paradas"]) == 15
    assert len(m["atividades_roteiro"]) == 30
    for papel in EMAILS_SEED:
        headers = login(client, papel)
        assert client.get("/usuarios/me", headers=headers).status_code == 200
    headers = login(client, "criador")
    pagina = client.get("/viagens", headers=headers).json()
    assert len(pagina["itens"]) == 20
    assert pagina["tem_proxima"] is True
    segunda = client.get("/viagens?pagina=2", headers=headers).json()
    assert len(segunda["itens"]) == 3
    assert segunda["tem_proxima"] is False
    assert client.get("/viagens", headers=login(client, "vazio")).json()["itens"] == []
    assert db_session.scalar(select(func.count()).select_from(SeedDemonstracaoModel)) == 1


@pytest.mark.parametrize(
    "papel,leitura,escrita",
    [
        ("criador", 200, 200),
        ("editor", 200, 200),
        ("visualizador", 200, 403),
        ("externo", 404, 404),
    ],
)
def test_permissoes_e_roteiro_preenchido(client, cenario_seed, papel, leitura, escrita):
    m = cenario_seed
    headers = login(client, papel)
    viagem = m["viagens"]["compartilhada"]
    parada = m["paradas"]["compartilhada-parada-1"]
    atividade = m["atividades_roteiro"]["compartilhada-parada-1-pendente"]
    base = f"/viagens/{viagem}/destinos/{parada}/atividades"
    resposta = client.get(base, headers=headers)
    assert resposta.status_code == leitura
    if leitura == 200:
        assert [a["status"] for a in resposta.json()] == ["confirmada", "pendente", "concluida"]
        assert resposta.json()[-1]["realizada_em"] is not None
    assert (
        client.patch(
            f"{base}/{atividade}", headers=headers, json={"custo_previsto": "50.00"}
        ).status_code
        == escrita
    )


def test_catalogos_publicos_filtros_paginacao(client, cenario_seed):
    destinos = client.get("/catalogo/destinos?nome=Demo").json()
    assert len(destinos["itens"]) == 20
    assert destinos["tem_proxima"] is True
    assert len(client.get("/catalogo/destinos?nome=Demo&pais_codigo=PT").json()["itens"]) == 2
    atividades = client.get("/catalogo/atividades?nome=Demo&categoria=cultura").json()
    assert len(atividades["itens"]) == 20
    assert atividades["tem_proxima"] is True


def test_reexecutar_preserva_edicoes_senhas_e_exclusoes(db_session, cenario_seed):
    usuario = db_session.get(UsuarioModel, cenario_seed["usuarios"]["criador"])
    usuario.nome, usuario.senha_hash = "Nome alterado", "hash-alterado"
    viagem = db_session.get(ViagemModel, cenario_seed["viagens"]["paginacao-01"])
    db_session.delete(viagem)
    db_session.flush()
    criado, manifesto = executar_seed_completo(CONFIG, db_session.connection(), date(2030, 1, 1))
    db_session.expire_all()
    assert not criado
    assert manifesto == cenario_seed
    assert usuario.nome == "Nome alterado"
    assert usuario.senha_hash == "hash-alterado"
    assert db_session.get(ViagemModel, cenario_seed["viagens"]["paginacao-01"]) is None
    assert db_session.scalar(select(func.count()).select_from(CatalogoAtividadeModel)) == 144


def test_falha_tardia_desfaz_toda_carga(db_session, monkeypatch):
    def falhar(self, chave, manifesto):
        raise RuntimeError("Falha simulada no fim")

    models = (
        UsuarioModel,
        ViagemModel,
        DestinoCatalogoModel,
        CatalogoAtividadeModel,
        AtividadeViagemModel,
        SeedDemonstracaoModel,
    )
    antes = {model: db_session.scalar(select(func.count()).select_from(model)) for model in models}
    monkeypatch.setattr(SQLAlchemySeedDemonstracaoRepository, "concluir", falhar)
    with pytest.raises(RuntimeError, match="Falha simulada"):
        executar_seed_completo(CONFIG, db_session.connection(), REFERENCIA)
    for model in (
        UsuarioModel,
        ViagemModel,
        DestinoCatalogoModel,
        CatalogoAtividadeModel,
        AtividadeViagemModel,
        SeedDemonstracaoModel,
    ):
        assert db_session.scalar(select(func.count()).select_from(model)) == antes[model]


@pytest.mark.parametrize("ambiente", ["production", "staging", "test"])
def test_bloqueio_antes_de_acessar_banco(ambiente):
    config = carregar_settings({"APP_ENV": ambiente})
    with pytest.raises(PermissionError):
        executar_seed_completo(config, None, REFERENCIA)


def test_colisao_de_email_nao_apropria_conta(db_session):
    antes = db_session.scalar(select(func.count()).select_from(UsuarioModel))
    db_session.add(
        UsuarioModel(nome="Existente", email=EMAILS_SEED["editor"], senha_hash="original")
    )
    db_session.flush()
    from app.domain.errors import DadosInvalidos

    with pytest.raises(DadosInvalidos, match="Email reservado"):
        executar_seed_completo(CONFIG, db_session.connection(), REFERENCIA)
    assert db_session.scalar(select(func.count()).select_from(UsuarioModel)) == antes + 1
    assert db_session.scalar(select(func.count()).select_from(ViagemModel)) == 0


def test_crud_isolamento_e_exclusao_com_cenarios(client, cenario_seed):
    m = cenario_seed
    dono = login(client, "criador")
    editor = login(client, "editor")
    viagem = m["viagens"]["compartilhada"]
    privada = m["viagens"]["privada"]
    outra_parada = m["paradas"]["compartilhada-parada-2"]
    atividade = m["atividades_roteiro"]["compartilhada-parada-1-pendente"]
    assert client.get(f"/viagens/{privada}", headers=dono).status_code == 404
    assert client.get(f"/viagens/{viagem}", headers=editor).status_code == 200
    base = f"/viagens/{viagem}/destinos"
    assert (
        client.get(f"{base}/{outra_parada}/atividades/{atividade}", headers=dono).status_code == 404
    )
    ids = [m["paradas"][f"compartilhada-parada-{i}"] for i in (3, 2, 1)]
    assert (
        client.put(f"{base}/ordem", headers=editor, json={"destinos_ids": ids}).status_code == 200
    )
    # Cenário próprio descartável evita destruir os exemplos colaborativos.
    descartavel = login(client, "descartavel")
    id_descartavel = m["viagens"]["descartavel"]
    assert client.delete(f"/viagens/{id_descartavel}", headers=descartavel).status_code == 204
    assert client.get(f"/viagens/{id_descartavel}", headers=descartavel).status_code == 404
    assert (
        client.get(
            f"/catalogo/atividades/{m['atividades_catalogo']['destino-01-cultura']}"
        ).status_code
        == 200
    )
    assert client.delete("/usuarios/me", headers=descartavel).status_code == 204
    assert client.get("/usuarios/me", headers=descartavel).status_code == 401


def test_conta_descartavel_permite_troca_senha_e_logout(client, cenario_seed):
    headers = login(client, "descartavel")
    assert (
        client.patch("/usuarios/me", headers=headers, json={"nome": "Novo nome"}).status_code == 200
    )
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
        "/auth/login",
        json={
            "email": EMAILS_SEED["descartavel"],
            "senha": "OutraSenha123!",
        },
    )
    headers = {"Authorization": "Bearer " + resposta.json()["access_token"]}
    assert client.get("/usuarios/resumo", headers=headers).status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/usuarios/me", headers=headers).status_code == 401


def test_lock_permanece_ate_confirmacao_externa(db_session, cenario_seed):
    from sqlalchemy import text

    from app.infrastructure.database import engine

    with engine.connect() as outra:
        assert outra.scalar(text("SELECT pg_try_advisory_xact_lock(202647, 1)")) is False
