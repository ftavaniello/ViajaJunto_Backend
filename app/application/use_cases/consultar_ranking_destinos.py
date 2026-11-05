from dataclasses import replace

from app.domain.errors import DadosInvalidos
from app.domain.ports.avaliacoes_destino_repository import AvaliacoesDestinoRepository
from app.domain.ports.ranking_destinos_cache import RankingDestinosCache
from app.domain.ranking_destinos import RankingDestinos, ranquear_destinos

LIMITE_MAXIMO = 50


class ConsultarRankingDestinos:
    """Destinos mais bem avaliados para a página inicial (RF25). Consulta pública."""

    def __init__(
        self, repository: AvaliacoesDestinoRepository, cache: RankingDestinosCache | None = None
    ):
        self.repository = repository
        self.cache = cache

    def execute(self, limite: int = 10) -> RankingDestinos:
        return self.execute_com_origem(limite)[0]

    def execute_com_origem(self, limite: int = 10) -> tuple[RankingDestinos, str]:
        if type(limite) is not int or not 1 <= limite <= LIMITE_MAXIMO:
            raise DadosInvalidos(f"Limite deve estar entre 1 e {LIMITE_MAXIMO}")
        snapshot, disponivel, versao = self.cache.ler() if self.cache else (None, False, None)
        if snapshot is not None:
            return replace(snapshot, itens=snapshot.itens[:limite]), "HIT"
        snapshot = ranquear_destinos(self.repository.agregar_por_destino(), LIMITE_MAXIMO)
        origem = "BYPASS"
        if disponivel and versao is not None and self.cache.gravar(snapshot, versao):
            origem = "MISS"
        return replace(snapshot, itens=snapshot.itens[:limite]), origem
