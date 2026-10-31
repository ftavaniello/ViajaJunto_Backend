from abc import ABC, abstractmethod

from app.domain.enums import PapelMembro


class MembroViagemRepository(ABC):
    @abstractmethod
    def buscar_papel(self, viagem_id: int, usuario_id: int) -> PapelMembro | None:
        """Papel do colaborador na viagem, ou None se ele nao e membro.

        O criador nao e membro: ele e identificado por `Viagem.criador_id`.
        """
        pass
