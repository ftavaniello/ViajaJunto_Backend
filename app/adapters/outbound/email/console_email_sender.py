import logging

from app.domain.ports.email_sender import EmailSender, MensagemEmail

logger = logging.getLogger(__name__)


class ConsoleEmailSender(EmailSender):
    """Escreve o email no log em vez de envia-lo. So para desenvolvimento.

    O corpo contem o link de redefinicao: nunca use este adaptador em producao.
    """

    def enviar(self, mensagem: MensagemEmail) -> None:
        logger.warning(
            "EMAIL (backend console)\nPara: %s\nAssunto: %s\n\n%s",
            mensagem.destinatario,
            mensagem.assunto,
            mensagem.corpo,
        )
