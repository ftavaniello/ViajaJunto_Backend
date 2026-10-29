from unittest.mock import Mock

import pytest
from redis import ConnectionError

from app.adapters.outbound.cache.redis_total_usuarios_cache import RedisTotalUsuariosCache
from app.infrastructure.cache import get_total_usuarios_cache
from app.infrastructure.config import settings


@pytest.mark.parametrize("value", ["invalid", "-1", b"\xff"])
def test_valor_invalido_e_tratado_como_miss(value):
    client = Mock()
    client.get.return_value = value
    assert RedisTotalUsuariosCache(client).ler() == (None, True)


def test_escrita_indisponivel_retorna_false():
    client = Mock()
    client.set.side_effect = ConnectionError("offline")
    assert RedisTotalUsuariosCache(client).gravar(4) is False


def test_cache_desativado():
    cache = RedisTotalUsuariosCache(None)
    assert cache.ler() == (None, False)
    assert cache.gravar(4) is False
    cache.invalidar()


def test_endpoint_descoberto_em_arquivo(tmp_path, monkeypatch):
    endpoint = tmp_path / "redis-url"
    endpoint.write_text("redis://localhost:6379/0\n", encoding="utf-8")
    monkeypatch.setattr(settings, "REDIS_URL", "")
    monkeypatch.setattr(settings, "REDIS_URL_FILE", str(endpoint))
    cache = get_total_usuarios_cache()
    assert cache.client.connection_pool.connection_kwargs["host"] == "localhost"
    assert cache.client.connection_pool.connection_kwargs["socket_timeout"] == 0.5


def test_arquivo_ausente_desativa_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", "")
    monkeypatch.setattr(settings, "REDIS_URL_FILE", str(tmp_path / "ausente"))
    assert get_total_usuarios_cache().ler() == (None, False)
