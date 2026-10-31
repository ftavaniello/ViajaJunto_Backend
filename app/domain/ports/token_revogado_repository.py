from abc import ABC, abstractmethod
from datetime import datetime


class TokenRevogadoRepository(ABC):
    """Lista de tokens encerrados por logout antes de expirarem.

    E consultada a cada requisicao autenticada: o armazenamento precisa ser
    duravel e a falha de leitura deve propagar (nunca tratar como "nao revogado").
    """

    @abstractmethod
    def revogar(self, jti: str, usuario_id: int, expira_em: datetime) -> None:
        pass

    @abstractmethod
    def esta_revogado(self, jti: str) -> bool:
        pass
