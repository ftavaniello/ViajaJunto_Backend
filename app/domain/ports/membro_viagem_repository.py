from abc import ABC, abstractmethod

from app.domain.enums import PapelMembro
from app.domain.membro_viagem import MembroViagem


class MembroViagemRepository(ABC):
    @abstractmethod
    def buscar_papel(self, viagem_id: int, usuario_id: int) -> PapelMembro | None:
        """Papel do colaborador na viagem, ou None se ele nao e membro.

        O criador nao e membro: ele e identificado por `Viagem.criador_id`.
        """
        pass

    @abstractmethod
    def adicionar(self, viagem_id: int, usuario_id: int, papel: PapelMembro) -> None:
        """Cria o vinculo; levanta MembroJaParticipa se ele ja existir."""
        pass

    @abstractmethod
    def alterar_papel(self, viagem_id: int, usuario_id: int, papel: PapelMembro) -> None:
        pass

    @abstractmethod
    def remover(self, viagem_id: int, usuario_id: int) -> None:
        pass

    @abstractmethod
    def listar(self, viagem_id: int) -> list[MembroViagem]:
        """Colaboradores da viagem por ordem de entrada."""
        pass
