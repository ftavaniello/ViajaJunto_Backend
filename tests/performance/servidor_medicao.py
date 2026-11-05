"""Servidor exclusivo do benchmark: cache de contagem em BYPASS, sem seeds."""

from app.adapters.outbound.cache.redis_total_usuarios_cache import RedisTotalUsuariosCache
from app.infrastructure.cache import get_total_usuarios_cache
from app.main import app

app.dependency_overrides[get_total_usuarios_cache] = lambda: RedisTotalUsuariosCache(None)
