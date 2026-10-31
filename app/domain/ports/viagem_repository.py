from abc import ABC, abstractmethod

from app.domain.entities.viagem import Viagem
from app.domain.participacao_viagem import ParticipacaoViagem


class ViagemRepository(ABC):
    @abstractmethod
    def salvar(self, viagem: Viagem) -> Viagem:
        pass

    @abstractmethod
    def buscar_por_id(self, viagem_id: int) -> Viagem | None:
        pass

    @abstractmethod
    def listar_por_participante(
        self, usuario_id: int, limite: int, deslocamento: int
    ) -> list[ParticipacaoViagem]:
        """Viagens e vínculos atuais, sem duplicação, por data_inicio e id crescentes.

        Aplica limite e deslocamento na persistência; inclui próprias e compartilhadas.
        """
        pass

    @abstractmethod
    def deletar(self, viagem_id: int) -> None:
        """Remove a viagem e tudo que depende dela (membros, roteiro, orcamento)."""
        pass
