from abc import ABC, abstractmethod

from app.domain.ranking_destinos import AvaliacoesDestino


class AvaliacoesDestinoRepository(ABC):
    @abstractmethod
    def agregar_por_destino(self) -> list[AvaliacoesDestino]:
        """Total e soma das notas das atividades de cada destino com ao menos uma avaliação.

        Fonte persistente; o caso de uso pode reutilizar um snapshot por cache.
        """
        pass
