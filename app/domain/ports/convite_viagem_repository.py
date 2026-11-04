from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.convite_viagem import ConviteViagem


class ConviteViagemRepository(ABC):
    @abstractmethod
    def salvar(self, convite: ConviteViagem) -> ConviteViagem:
        """Insere o convite ou grava o aceite de um convite existente."""
        pass

    @abstractmethod
    def buscar_por_hash(self, token_hash: str) -> ConviteViagem | None:
        pass

    @abstractmethod
    def buscar(self, viagem_id: int, convite_id: int) -> ConviteViagem | None:
        pass

    @abstractmethod
    def listar_pendentes(self, viagem_id: int, agora: datetime) -> list[ConviteViagem]:
        """Convites nao aceitos e ainda validos, do mais antigo ao mais novo."""
        pass

    @abstractmethod
    def remover(self, convite_id: int) -> None:
        pass

    @abstractmethod
    def remover_pendentes(self, viagem_id: int, email: str) -> None:
        """Invalida convites ainda nao aceitos deste email nesta viagem (reenvio)."""
        pass
