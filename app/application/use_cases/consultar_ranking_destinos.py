from app.domain.errors import DadosInvalidos
from app.domain.ports.avaliacoes_destino_repository import AvaliacoesDestinoRepository
from app.domain.ranking_destinos import RankingDestinos, ranquear_destinos

LIMITE_MAXIMO = 50


class ConsultarRankingDestinos:
    """Destinos mais bem avaliados para a página inicial (RF25). Consulta pública."""

    def __init__(self, repository: AvaliacoesDestinoRepository):
        self.repository = repository

    def execute(self, limite: int = 10) -> RankingDestinos:
        if type(limite) is not int or not 1 <= limite <= LIMITE_MAXIMO:
            raise DadosInvalidos(f"Limite deve estar entre 1 e {LIMITE_MAXIMO}")
        return ranquear_destinos(self.repository.agregar_por_destino(), limite)
