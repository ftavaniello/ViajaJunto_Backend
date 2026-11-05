from abc import ABC, abstractmethod

from app.domain.entities.atividade_viagem import AtividadeViagem


class AtividadeViagemRepository(ABC):
    @abstractmethod
    def listar(self, viagem_id: int, destino_id: int) -> list[AtividadeViagem]:
        """Ordena por data, horário (nulos ao fim de cada dia) e id, dentro da viagem/parada."""
        pass

    @abstractmethod
    def buscar(self, viagem_id: int, destino_id: int, atividade_id: int) -> AtividadeViagem | None:
        pass

    @abstractmethod
    def salvar(self, atividade: AtividadeViagem) -> AtividadeViagem:
        pass

    @abstractmethod
    def deletar(self, atividade: AtividadeViagem) -> None:
        """Exclui só o planejamento; preserva catálogo e avaliações públicas."""
        pass
