import os
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from redis import ConnectionError, Redis

from app.adapters.outbound.cache.redis_ranking_destinos_cache import RedisRankingDestinosCache
from app.application.use_cases.consultar_ranking_destinos import ConsultarRankingDestinos
from app.domain.entities.catalogo import DestinoCatalogo
from app.domain.ranking_destinos import AvaliacoesDestino
from app.infrastructure.dependencies import get_consultar_ranking_destinos
from app.main import app


@pytest.fixture
def cache():
    url = os.getenv("TEST_REDIS_URL")
    if not url:
        pytest.skip("Defina TEST_REDIS_URL para testar com Redis real")
    client = Redis.from_url(url, decode_responses=True)
    client.ping()
    cache = RedisRankingDestinosCache(client, ttl=30)
    cache.key = "teste:ranking:" + uuid4().hex
    cache.version_key = cache.key + ":versao"
    try:
        yield cache
    finally:
        client.delete(cache.key, cache.version_key)
        client.close()


def caso(cache):
    repo = Mock()
    repo.agregar_por_destino.return_value = [
        AvaliacoesDestino(
            destino=DestinoCatalogo(id=1, nome="Roma", pais_codigo="IT"),
            total_avaliacoes=2,
            soma_notas=9,
        ),
        AvaliacoesDestino(
            destino=DestinoCatalogo(id=2, nome="Rio", pais_codigo="BR"),
            total_avaliacoes=1,
            soma_notas=3,
        ),
    ]
    return ConsultarRankingDestinos(repo, cache), repo


def test_miss_hit_limites_e_serializacao_preservam_resultado(cache):
    consulta, repo = caso(cache)
    primeiro, origem = consulta.execute_com_origem(1)
    assert origem == "MISS" and len(primeiro.itens) == 1
    segundo, origem = consulta.execute_com_origem(50)
    assert origem == "HIT" and len(segundo.itens) == 2
    assert segundo.itens[0] == primeiro.itens[0]
    repo.agregar_por_destino.assert_called_once()
    assert 0 < cache.client.ttl(cache.key) <= 30


def test_invalidacao_e_corrida_nao_reintroduzem_snapshot_antigo(cache):
    consulta, repo = caso(cache)
    snapshot = consulta.execute()
    _, _, versao = cache.ler()
    cache.invalidar()
    assert cache.gravar(snapshot, versao) is False
    assert consulta.execute_com_origem()[1] == "MISS"
    assert repo.agregar_por_destino.call_count == 2


def test_expiracao_e_json_corrompido_recalculam(cache):
    consulta, repo = caso(cache)
    consulta.execute()
    cache.client.pexpire(cache.key, 1)
    # Force expiry without sleeping; Redis deletes the key when expiry is in the past.
    cache.client.pexpireat(cache.key, 1)
    assert consulta.execute_com_origem()[1] == "MISS"
    cache.client.set(cache.key, "json inválido")
    assert consulta.execute_com_origem()[1] == "MISS"
    assert repo.agregar_por_destino.call_count == 3


def test_ranking_vazio_tambem_e_cacheado(cache):
    consulta, repo = caso(cache)
    repo.agregar_por_destino.return_value = []
    assert consulta.execute_com_origem()[1] == "MISS"
    resultado, origem = consulta.execute_com_origem()
    assert resultado.itens == [] and resultado.media_geral is None and origem == "HIT"
    repo.agregar_por_destino.assert_called_once()


def test_indisponibilidade_nao_impede_consulta():
    client = Mock()
    client.mget.side_effect = ConnectionError("offline")
    consulta, repo = caso(RedisRankingDestinosCache(client))
    assert consulta.execute_com_origem()[1] == "BYPASS"
    repo.agregar_por_destino.assert_called_once()
    client.pipeline.side_effect = ConnectionError("offline")
    RedisRankingDestinosCache(client).invalidar()
    client.eval.side_effect = ConnectionError("offline")
    assert RedisRankingDestinosCache(client).gravar(consulta.execute(), "0") is False


def test_headers_http_e_contrato_iguais_entre_miss_e_hit(cache):
    consulta, repo = caso(cache)
    app.dependency_overrides[get_consultar_ranking_destinos] = lambda: consulta
    try:
        with TestClient(app) as client:
            primeiro = client.get("/catalogo/destinos/ranking?limite=1")
            segundo = client.get("/catalogo/destinos/ranking?limite=1")
            assert primeiro.status_code == segundo.status_code == 200
            assert primeiro.json() == segundo.json()
            assert primeiro.headers["X-Cache"] == "MISS"
            assert segundo.headers["X-Cache"] == "HIT"
            assert segundo.headers["Cache-Control"] == "no-store"
            assert client.get("/catalogo/destinos/ranking?limite=51").status_code == 422
    finally:
        app.dependency_overrides.pop(get_consultar_ranking_destinos, None)
    repo.agregar_por_destino.assert_called_once()
