from abc import ABC, abstractmethod

from app.domain.entities.viagem import Viagem


class ViagemRepository(ABC):
    @abstractmethod
    def salvar(self, viagem: Viagem) -> Viagem:
        pass

    @abstractmethod
    def buscar_por_id(self, viagem_id: int) -> Viagem | None:
        pass

    @abstractmethod
    def listar_por_participante(self, usuario_id: int) -> list[Viagem]:
        """Viagens criadas pelo usuario ou das quais ele e colaborador."""
        pass

    @abstractmethod
    def deletar(self, viagem_id: int) -> None:
        """Remove a viagem e tudo que depende dela (membros, roteiro, orcamento)."""
        pass
