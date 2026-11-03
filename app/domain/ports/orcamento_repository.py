from abc import ABC, abstractmethod
from decimal import Decimal

from app.domain.entities.orcamento import Orcamento
from app.domain.enums import CategoriaAtividade


class OrcamentoRepository(ABC):
    @abstractmethod
    def buscar(self, viagem_id: int) -> Orcamento | None:
        """Orçamento da viagem, ou None se ainda não foi definido."""
        pass

    @abstractmethod
    def salvar(self, orcamento: Orcamento) -> Orcamento:
        """Cria ou substitui o orçamento único da viagem."""
        pass

    @abstractmethod
    def custos_por_categoria(self, viagem_id: int) -> dict[CategoriaAtividade, Decimal]:
        """Soma dos custos previstos das atividades da viagem, exceto canceladas.

        Calculado a partir das atividades a cada consulta: não há total persistido
        que possa ficar desatualizado após incluir, editar ou remover atividades.
        Categorias sem atividades podem ser omitidas.
        """
        pass
