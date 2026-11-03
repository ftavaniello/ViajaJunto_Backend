from app.adapters.outbound.persistence.catalogo_repository_memory import CatalogoRepositoryMemory
from app.domain.ports.avaliacoes_destino_repository import AvaliacoesDestinoRepository
from app.domain.ranking_destinos import AvaliacoesDestino


class AvaliacoesDestinoRepositoryMemory(AvaliacoesDestinoRepository):
    """Notas por atividade do catálogo; faz o papel do JOIN com o destino da atividade."""

    def __init__(self, catalogo: CatalogoRepositoryMemory):
        self.catalogo = catalogo
        self.notas: list[tuple[int, int]] = []  # (catalogo_atividade_id, nota)

    def avaliar(self, catalogo_atividade_id: int, nota: int) -> None:
        # Ainda não faz parte da porta: o registro de avaliações chega com a #23.
        self.notas.append((catalogo_atividade_id, nota))

    def agregar_por_destino(self) -> list[AvaliacoesDestino]:
        totais: dict[int, tuple[int, int]] = {}
        for atividade_id, nota in self.notas:
            destino_id = self.catalogo.atividades[atividade_id].destino.id
            total, soma = totais.get(destino_id, (0, 0))
            totais[destino_id] = (total + 1, soma + nota)
        return [
            AvaliacoesDestino(
                destino=self.catalogo.destinos[destino_id], total_avaliacoes=total, soma_notas=soma
            )
            for destino_id, (total, soma) in totais.items()
        ]
