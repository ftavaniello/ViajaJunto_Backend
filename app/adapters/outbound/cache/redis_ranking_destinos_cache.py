import logging
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError
from redis import Redis, RedisError

from app.domain.errors import DadosInvalidos
from app.domain.ports.ranking_destinos_cache import RankingDestinosCache
from app.domain.ranking_destinos import RankingDestinos

logger = logging.getLogger(__name__)
SERIALIZADOR = TypeAdapter(RankingDestinos)


class RedisRankingDestinosCache(RankingDestinosCache):
    """Um snapshot dos 50 primeiros; a versão protege a corrida com invalidação."""

    def __init__(self, client: Redis | None, ttl: int = 60):
        self.client = client
        self.ttl = ttl
        self.key = "viajajunto:ranking:destinos:v1"
        self.version_key = self.key + ":versao"

    def ler(self) -> tuple[RankingDestinos | None, bool, str | None]:
        if self.client is None:
            return None, False, None
        versao = "0"
        try:
            versao, conteudo = self.client.mget(self.version_key, self.key)
            if conteudo is None:
                return None, True, versao or "0"
            return SERIALIZADOR.validate_json(conteudo), True, versao or "0"
        except (ValidationError, DadosInvalidos, ValueError, UnicodeError):
            logger.warning("Ranking em cache inválido; consultando PostgreSQL")
            return None, True, versao or "0"
        except RedisError:
            logger.warning("Cache do ranking indisponível; consultando PostgreSQL")
            return None, False, None

    def gravar(self, ranking: RankingDestinos, versao: str) -> bool:
        if self.client is None:
            return False
        try:
            # Não repõe um snapshot antigo se uma escrita invalidou durante a consulta SQL.
            return bool(
                self.client.eval(
                    "if (redis.call('GET', KEYS[1]) or '0') ~= ARGV[1] then return 0 end "
                    "redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3]); return 1",
                    2,
                    self.version_key,
                    self.key,
                    versao,
                    SERIALIZADOR.dump_json(ranking),
                    self.ttl,
                )
            )
        except RedisError:
            logger.warning("Não foi possível preencher o cache do ranking")
            return False

    def invalidar(self) -> None:
        if self.client is None:
            return
        try:
            with self.client.pipeline(transaction=True) as pipe:
                pipe.set(self.version_key, uuid4().hex)
                pipe.delete(self.key)
                pipe.execute()
        except RedisError:
            logger.warning("Falha ao invalidar ranking; snapshot anterior expirará pelo TTL")
