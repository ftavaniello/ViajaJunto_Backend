from app.domain.ports.email_sender import EmailSender, FalhaEnvioEmail, MensagemEmail


class EmailSenderMemory(EmailSender):
    """Guarda as mensagens em lista, para testes. Com `falhar=True` simula servidor fora."""

    def __init__(self, falhar: bool = False):
        self.enviados: list[MensagemEmail] = []
        self.falhar = falhar

    def enviar(self, mensagem: MensagemEmail) -> None:
        if self.falhar:
            raise FalhaEnvioEmail("Servidor de email indisponivel")
        self.enviados.append(mensagem)
