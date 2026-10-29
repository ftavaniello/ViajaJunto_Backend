import logging

from redis import Redis, RedisError

from app.domain.ports.total_usuarios_cache import TotalUsuariosCache

logger = logging.getLogger(__name__)


class RedisTotalUsuariosCache(TotalUsuariosCache):
    def __init__(self, client: Redis | None, ttl: int = 60,
                 key: str = "viajajunto:usuarios:total:v1"):
        self.client = client
        self.ttl = ttl
        self.key = key

    def ler(self) -> tuple[int | None, bool]:
        if self.client is None:
            return None, False
        try:
            value = self.client.get(self.key)
            if value is None:
                return None, True
            total = int(value)
            if total < 0:
                raise ValueError("Total negativo")
            return total, True
        except (ValueError, UnicodeError):
            logger.warning("Total em cache invalido; consultando PostgreSQL")
            return None, True
        except RedisError:
            logger.warning("Cache indisponivel; consultando PostgreSQL")
            return None, False

    def gravar(self, total: int) -> bool:
        if self.client is None:
            return False
        try:
            return bool(self.client.set(self.key, str(total), ex=self.ttl))
        except RedisError:
            logger.warning("Nao foi possivel preencher o cache")
            return False

    def invalidar(self) -> None:
        if self.client is None:
            return
        try:
            self.client.delete(self.key)
        except RedisError:
            logger.warning("Falha ao invalidar total; o valor anterior expirara pelo TTL")
