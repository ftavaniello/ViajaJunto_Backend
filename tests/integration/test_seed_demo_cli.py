from contextlib import contextmanager
from datetime import date
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.inbound.cli import seed_demo
from app.infrastructure.config import carregar_settings


@pytest.mark.parametrize("criado", [True, False])
def test_cli_invalida_cache_somente_apos_commit(monkeypatch, capsys, criado):
    eventos = []

    @contextmanager
    def transacao():
        eventos.append("inicio")
        yield object()
        eventos.append("commit")

    def invalidar():
        assert eventos == ["inicio", "commit"]
        eventos.append("cache")

    cache = Mock()
    cache.invalidar.side_effect = invalidar
    monkeypatch.setattr(seed_demo, "settings", carregar_settings({"APP_ENV": "development"}))
    monkeypatch.setattr(seed_demo.engine, "begin", transacao)
    monkeypatch.setattr(seed_demo, "get_total_usuarios_cache", lambda: cache)
    monkeypatch.setattr(seed_demo, "executar_seed_completo", lambda *args: (criado, {"id": 42}))
    monkeypatch.setattr("sys.argv", ["seed_demo", "--completo", "--referencia", "2027-01-15"])
    assert seed_demo.main() == 0
    assert eventos == (["inicio", "commit", "cache"] if criado else ["inicio", "commit"])
    assert '"id": 42' in capsys.readouterr().out


def test_cli_bloqueia_antes_de_abrir_conexao(monkeypatch):
    monkeypatch.setattr(seed_demo, "settings", carregar_settings({"APP_ENV": "production"}))
    begin = Mock()
    monkeypatch.setattr(seed_demo.engine, "begin", begin)
    assert seed_demo.carregar_cenarios(date(2027, 1, 15)) == 1
    begin.assert_not_called()


def test_cli_falha_sem_expor_detalhes_da_conexao(monkeypatch, capsys):
    monkeypatch.setattr(seed_demo, "settings", carregar_settings({"APP_ENV": "development"}))
    monkeypatch.setattr(seed_demo.engine, "begin", Mock(side_effect=SQLAlchemyError("segredo")))
    assert seed_demo.carregar_cenarios(date(2027, 1, 15)) == 1
    mensagem = capsys.readouterr().err
    assert "carga desfeita" in mensagem
    assert "segredo" not in mensagem


def test_cli_referencia_exige_modo_completo(monkeypatch):
    monkeypatch.setattr("sys.argv", ["seed_demo", "--referencia", "2027-01-15"])
    with pytest.raises(SystemExit) as error:
        seed_demo.main()
    assert error.value.code == 2
