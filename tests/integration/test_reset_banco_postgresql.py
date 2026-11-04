from datetime import date
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.infrastructure import reset_banco as infra
from app.infrastructure.config import carregar_settings

CONFIG = carregar_settings({"APP_ENV": "development"})


def verificar_banco_teste(conexao):
    assert conexao.scalar(text("SELECT current_database()")).endswith("_test")


def test_reset_reaplica_migracoes_e_seed_atualizado(db_session):
    conexao = db_session.connection()
    verificar_banco_teste(conexao)
    conexao.execute(
        text(
            "INSERT INTO usuarios(nome,email,senha_hash) "
            "VALUES ('Antigo','antigo@example.com','hash')"
        )
    )
    manifesto = infra._recriar_schema(conexao, CONFIG, date(2027, 1, 15))
    assert (
        conexao.scalar(text("SELECT count(*) FROM usuarios WHERE email='antigo@example.com'")) == 0
    )
    for tabela, total in [
        ("usuarios", 6),
        ("viagens", 27),
        ("destinos_catalogo", 4),
        ("catalogo_atividades", 24),
        ("avaliacoes", 20),
        ("seeds_demonstracao", 1),
    ]:
        assert conexao.scalar(text(f"SELECT count(*) FROM {tabela}")) == total
    assert set(conexao.scalars(text("SELECT nome FROM destinos_catalogo"))) == {
        "Orlando",
        "Miami",
        "Rio de Janeiro",
        "Roma",
    }
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "alembic"))
    assert (
        conexao.scalar(text("SELECT version_num FROM alembic_version"))
        == ScriptDirectory.from_config(config).get_current_head()
    )
    assert manifesto["referencia"] == "2027-01-15"


def test_falha_do_seed_restaura_schema_e_dados_antigos(db_session, monkeypatch):
    conexao = db_session.connection()
    verificar_banco_teste(conexao)
    conexao.execute(
        text(
            "INSERT INTO usuarios(nome,email,senha_hash) "
            "VALUES ('Preservado','preservado@example.com','hash')"
        )
    )
    versao = conexao.scalar(text("SELECT version_num FROM alembic_version"))
    seed = infra.executar_seed_completo

    def falhar(*args):
        seed(*args)
        raise RuntimeError("Falha após o seed")

    monkeypatch.setattr(infra, "executar_seed_completo", falhar)
    with pytest.raises(RuntimeError, match="Falha após o seed"):
        with conexao.begin_nested():
            infra._recriar_schema(conexao, CONFIG, date(2027, 1, 15))
    assert (
        conexao.scalar(text("SELECT nome FROM usuarios WHERE email='preservado@example.com'"))
        == "Preservado"
    )
    assert conexao.scalar(text("SELECT version_num FROM alembic_version")) == versao
