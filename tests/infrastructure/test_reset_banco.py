from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.inbound.cli import reset_banco as cli
from app.infrastructure import reset_banco as infra
from app.infrastructure.config import carregar_settings

URL_LOCAL = "postgresql+psycopg2://viajajunto:senha@db:5432/viajajunto"


def config(**valores):
    return carregar_settings({"APP_ENV": "development", "DATABASE_URL": URL_LOCAL, **valores})


@pytest.mark.parametrize("env", ["production", "staging", "test"])
def test_recusa_outros_ambientes_antes_de_abrir_conexao(monkeypatch, env):
    criar = Mock()
    monkeypatch.setattr(infra, "create_engine", criar)
    with pytest.raises(PermissionError):
        infra.resetar_banco(config(APP_ENV=env), confirmar=True)
    criar.assert_not_called()


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg2://u:p@localhost:5432/viajajunto",
        "postgresql+psycopg2://u:p@127.0.0.1:5432/viajajunto",
        "postgresql+psycopg2://u:p@remoto:5432/viajajunto",
        "postgresql+psycopg2://u:p@db:5433/viajajunto",
        "postgresql+psycopg2://u:p@db:5432/viajajunto_test",
        "postgresql+psycopg2://u:p@db:5432/producao",
        "postgresql+psycopg2://u:p@db:5432/viajajunto?options=-csearch_path%3Doutro",
        "sqlite:///teste.db",
    ],
)
def test_recusa_destinos_diferentes_antes_de_conectar(monkeypatch, url):
    criar = Mock()
    monkeypatch.setattr(infra, "create_engine", criar)
    with pytest.raises(PermissionError):
        infra.resetar_banco(config(DATABASE_URL=url), confirmar=True)
    criar.assert_not_called()


def test_exige_confirmacao_tambem_na_infraestrutura(monkeypatch):
    criar = Mock()
    monkeypatch.setattr(infra, "create_engine", criar)
    with pytest.raises(PermissionError, match="confirmar"):
        infra.resetar_banco(config())
    criar.assert_not_called()


def test_nome_real_da_conexao_precisa_corresponder(monkeypatch):
    banco = MagicMock()
    conexao = banco.begin.return_value.__enter__.return_value
    conexao.scalar.return_value = "outro_banco"
    monkeypatch.setattr(infra, "create_engine", lambda *args, **kwargs: banco)
    recriar = Mock()
    monkeypatch.setattr(infra, "_recriar_schema", recriar)
    with pytest.raises(PermissionError, match="conectado"):
        infra.resetar_banco(config(), confirmar=True)
    recriar.assert_not_called()
    banco.dispose.assert_called_once()


def test_cli_sem_flag_nao_chama_reset(monkeypatch):
    reset = Mock()
    monkeypatch.setattr(cli, "resetar_banco", reset)
    monkeypatch.setattr("sys.argv", ["reset_banco"])
    with pytest.raises(SystemExit) as erro:
        cli.main()
    assert erro.value.code == 2
    reset.assert_not_called()


def test_cli_invalida_cache_somente_depois_do_reset(monkeypatch, capsys):
    eventos = []

    def reset(*args, **kwargs):
        assert kwargs["confirmar"] is True
        eventos.append("commit")
        return {
            "usuarios": dict(a=1),
            "destinos_catalogo": dict(a=1),
            "atividades_catalogo": dict(a=1),
        }

    cache = Mock()

    def invalidar():
        assert eventos == ["commit"]
        eventos.append("cache")

    cache.invalidar.side_effect = invalidar
    monkeypatch.setattr(cli, "resetar_banco", reset)
    monkeypatch.setattr(cli, "get_total_usuarios_cache", lambda: cache)
    monkeypatch.setattr("sys.argv", ["reset_banco", "--confirmar"])
    assert cli.main() == 0
    assert eventos == ["commit", "cache"]
    assert "recriado" in capsys.readouterr().out


@pytest.mark.parametrize(
    "erro", [PermissionError("bloqueado"), SQLAlchemyError("credencial-secreta")]
)
def test_cli_falha_sem_invalidar_cache_ou_expor_credenciais(monkeypatch, capsys, erro):
    cache = Mock()
    monkeypatch.setattr(cli, "resetar_banco", Mock(side_effect=erro))
    monkeypatch.setattr(cli, "get_total_usuarios_cache", lambda: cache)
    monkeypatch.setattr("sys.argv", ["reset_banco", "--confirmar"])
    assert cli.main() == 1
    assert "credencial-secreta" not in capsys.readouterr().err
    cache.invalidar.assert_not_called()
