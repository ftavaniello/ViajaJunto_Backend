from abc import ABC, abstractmethod

from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.enums import CategoriaAtividade


class CatalogoRepository(ABC):
    @abstractmethod
    def salvar_destino(self, destino: DestinoCatalogo) -> DestinoCatalogo:
        pass

    @abstractmethod
    def salvar_atividade(self, atividade: AtividadeCatalogo) -> AtividadeCatalogo:
        pass

    @abstractmethod
    def buscar_atividade(self, atividade_id: int) -> AtividadeCatalogo | None:
        pass

    @abstractmethod
    def listar_atividades(
        self,
        nome: str | None,
        categoria: CategoriaAtividade | None,
        localizacao: str | None,
        destino_catalogo_id: int | None,
        limite: int,
        deslocamento: int,
    ) -> list[AtividadeCatalogo]:
        """Filtros combinados por E; texto parcial sem distinguir caixa; ordem por id."""
        pass
