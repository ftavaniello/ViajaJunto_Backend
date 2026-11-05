from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class MensagemEmail:
    destinatario: str
    assunto: str
    corpo: str


class FalhaEnvioEmail(Exception):
    """O email nao pode ser entregue ao servidor de envio."""


class EmailSender(ABC):
    @abstractmethod
    def enviar(self, mensagem: MensagemEmail) -> None:
        """Envia a mensagem, ou levanta FalhaEnvioEmail se nao conseguir."""
        pass
