import os
import time
import uuid
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from redis import ConnectionError, Redis
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.adapters.outbound.redis_total_usuarios_cache import RedisTotalUsuariosCache
from app.infrastructure.cache import get_total_usuarios_cache
from app.infrastructure.database import get_db
from app.main import app


@pytest.fixture
def resumo_api():
    # Isolated SQL database: no production users or shared cache keys are changed.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    UsuarioModel.metadata.create_all(engine)
    queries = []
    event.listen(engine, "before_cursor_execute",
                 lambda conn, cursor, statement, params, context, many: queries.append(statement))
    session = Session(engine)
    saved = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_total_usuarios_cache] = lambda: RedisTotalUsuariosCache(None)
    try:
        with TestClient(app) as client:
            yield client, queries
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)
        session.close()
        engine.dispose()


@pytest.fixture
def cache_real():
    url = os.getenv("TEST_REDIS_URL")
    if not url:
        pytest.skip("Defina TEST_REDIS_URL para testar com Redis real")
    client = Redis.from_url(url, decode_responses=True, protocol=2,
                            socket_connect_timeout=1, socket_timeout=1)
    client.ping()  # If explicitly configured, unavailable Redis is a failure.
    cache = RedisTotalUsuariosCache(client, ttl=30, key="teste:resumo:" + uuid.uuid4().hex)
    try:
        yield cache
    finally:
        client.delete(cache.key)
        client.close()


def cadastrar(client, email):
    response = client.post("/usuarios", json={
        "nome": "Teste", "email": email, "senha": "senhaSegura123",
    })
    assert response.status_code == 201
    login = client.post("/auth/login", json={"email": email, "senha": "senhaSegura123"})
    assert login.status_code == 200
    return {"Authorization": "Bearer " + login.json()["access_token"]}


def test_sem_token_nao_acessa_cache(resumo_api):
    client, _ = resumo_api
    cache = Mock()
    app.dependency_overrides[get_total_usuarios_cache] = lambda: cache
    assert client.get("/usuarios/resumo").status_code == 401
    cache.ler.assert_not_called()


def test_indisponibilidade_nao_quebra_consulta_cadastro_ou_exclusao(resumo_api):
    client, _ = resumo_api
    redis = Mock()
    redis.get.side_effect = ConnectionError("offline")
    redis.delete.side_effect = ConnectionError("offline")
    app.dependency_overrides[get_total_usuarios_cache] = lambda: RedisTotalUsuariosCache(redis)
    auth = cadastrar(client, "offline@example.com")
    response = client.get("/usuarios/resumo", headers=auth)
    assert response.status_code == 200
    assert response.json() == {"total_usuarios": 1}
    assert response.headers["X-Cache"] == "BYPASS"
    assert client.delete("/usuarios/me", headers=auth).status_code == 204


def test_miss_hit_invalida_e_preserva_autenticacao(resumo_api, cache_real):
    client, queries = resumo_api
    app.dependency_overrides[get_total_usuarios_cache] = lambda: cache_real
    auth = cadastrar(client, "primeiro@example.com")
    queries.clear()
    first = client.get("/usuarios/resumo", headers=auth)
    assert first.json() == {"total_usuarios": 1}
    assert first.headers["X-Cache"] == "MISS"
    assert any("count(" in sql.lower() for sql in queries)
    assert 0 < cache_real.client.ttl(cache_real.key) <= 30
    assert cache_real.client.get(cache_real.key) == "1"

    queries.clear()
    second = client.get("/usuarios/resumo", headers=auth)
    assert second.headers["X-Cache"] == "HIT"
    assert not any("count(" in sql.lower() for sql in queries)
    assert any("SELECT" in sql for sql in queries)  # Authentication still checks the account.

    second_auth = cadastrar(client, "segundo@example.com")
    assert cache_real.client.get(cache_real.key) is None
    changed = client.get("/usuarios/resumo", headers=auth)
    assert changed.headers["X-Cache"] == "MISS"
    assert changed.json() == {"total_usuarios": 2}
    assert client.delete("/usuarios/me", headers=second_auth).status_code == 204
    assert cache_real.client.get(cache_real.key) is None
    assert client.get("/usuarios/resumo", headers=auth).json() == {"total_usuarios": 1}
    assert client.get("/usuarios/resumo", headers=second_auth).status_code == 401
    invalid = client.get("/usuarios/resumo", headers={"Authorization": "Bearer invalido"})
    assert invalid.status_code == 401


def test_ttl_expira_e_cache_invalido_e_recalculado(resumo_api, cache_real):
    cache_real.ttl = 1
    client, _ = resumo_api
    app.dependency_overrides[get_total_usuarios_cache] = lambda: cache_real
    auth = cadastrar(client, "ttl@example.com")
    assert client.get("/usuarios/resumo", headers=auth).headers["X-Cache"] == "MISS"
    deadline = time.monotonic() + 5
    while cache_real.client.exists(cache_real.key) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert cache_real.client.get(cache_real.key) is None
    assert client.get("/usuarios/resumo", headers=auth).headers["X-Cache"] == "MISS"
    cache_real.client.set(cache_real.key, "invalido", ex=2)
    response = client.get("/usuarios/resumo", headers=auth)
    assert response.headers["X-Cache"] == "MISS"
    assert response.json() == {"total_usuarios": 1}
