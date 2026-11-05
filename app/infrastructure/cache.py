import logging
from functools import lru_cache
from pathlib import Path

from redis import Redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from app.adapters.outbound.cache.redis_ranking_destinos_cache import RedisRankingDestinosCache
from app.adapters.outbound.cache.redis_total_usuarios_cache import RedisTotalUsuariosCache
from app.infrastructure.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _client(url: str) -> Redis:
    return Redis.from_url(
        url,
        decode_responses=True,
        protocol=2,
        socket_connect_timeout=0.5,
        socket_timeout=0.5,
        retry=Retry(NoBackoff(), 0),
    )


def _cache_client() -> Redis | None:
    url = settings.REDIS_URL
    if not url and settings.REDIS_URL_FILE:
        try:
            url = Path(settings.REDIS_URL_FILE).read_text(encoding="utf-8").strip()
        except OSError:
            logger.warning("Endpoint do cache indisponivel; usando PostgreSQL")
    return _client(url) if url else None


def get_total_usuarios_cache() -> RedisTotalUsuariosCache:
    return RedisTotalUsuariosCache(_cache_client(), settings.CACHE_TTL_SECONDS)


def get_ranking_destinos_cache() -> RedisRankingDestinosCache:
    return RedisRankingDestinosCache(_cache_client(), settings.CACHE_TTL_SECONDS)
