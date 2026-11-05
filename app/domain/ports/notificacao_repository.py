from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.notificacao import Notificacao


class NotificacaoRepository(ABC):
    @abstractmethod
    def adicionar(self, notificacoes: list[Notificacao]) -> None:
        """Grava na transacao corrente; so vale depois do commit do caso de uso."""
        pass

    @abstractmethod
    def listar_do_usuario(
        self, usuario_id: int, somente_nao_lidas: bool, limite: int, deslocamento: int
    ) -> list[Notificacao]:
        """Notificacoes do usuario: nao lidas primeiro, depois as mais recentes."""
        pass

    @abstractmethod
    def contar_nao_lidas(self, usuario_id: int) -> int:
        pass

    @abstractmethod
    def marcar_lida(
        self, usuario_id: int, notificacao_id: int, agora: datetime
    ) -> Notificacao | None:
        """Marca como lida se pertencer ao usuario; None se nao existir ou for alheia.

        Marcar de novo mantem o `lida_em` original.
        """
        pass

    @abstractmethod
    def marcar_todas_lidas(self, usuario_id: int, agora: datetime) -> int:
        """Marca as nao lidas do usuario e retorna quantas foram marcadas."""
        pass
