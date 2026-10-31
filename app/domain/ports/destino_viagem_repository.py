from abc import ABC, abstractmethod
from datetime import date

from app.domain.entities.destino_viagem import DestinoViagem


class DestinoViagemRepository(ABC):
    @abstractmethod
    def bloquear_roteiro(self, viagem_id: int) -> None:
        """Serializa alterações na viagem/roteiro até o fim da transação."""
        pass

    @abstractmethod
    def listar(self, viagem_id: int) -> list[DestinoViagem]:
        """Retorna paradas com dados do catálogo por ordem de visita e id."""
        pass

    @abstractmethod
    def buscar(self, viagem_id: int, destino_id: int) -> DestinoViagem | None:
        """Busca exclusivamente dentro da viagem informada."""
        pass

    @abstractmethod
    def salvar(self, destino: DestinoViagem) -> DestinoViagem:
        pass

    @abstractmethod
    def deletar(self, destino: DestinoViagem) -> None:
        """Exclui a parada e suas atividades, preservando o catálogo público."""
        pass

    @abstractmethod
    def datas_atividades(self, destino_id: int) -> list[date]:
        pass
