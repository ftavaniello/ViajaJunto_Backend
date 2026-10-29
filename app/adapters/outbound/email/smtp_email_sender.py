import smtplib
from email.message import EmailMessage

from app.domain.ports.email_sender import EmailSender, FalhaEnvioEmail, MensagemEmail


class SmtpEmailSender(EmailSender):
    """Envia por SMTP. Localmente aponta para o Mailpit (docs/recuperacao-de-senha.md)."""

    def __init__(
        self,
        host: str,
        port: int,
        remetente: str,
        usuario: str = "",
        senha: str = "",
        starttls: bool = False,
        timeout: float = 10,
    ):
        self.host = host
        self.port = port
        self.remetente = remetente
        self.usuario = usuario
        self.senha = senha
        self.starttls = starttls
        self.timeout = timeout

    def enviar(self, mensagem: MensagemEmail) -> None:
        email = EmailMessage()
        email["From"] = self.remetente
        email["To"] = mensagem.destinatario
        email["Subject"] = mensagem.assunto
        email.set_content(mensagem.corpo)

        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
                if self.starttls:
                    smtp.starttls()
                if self.usuario:
                    smtp.login(self.usuario, self.senha)
                smtp.send_message(email)
        except (smtplib.SMTPException, OSError) as error:
            raise FalhaEnvioEmail(f"Falha no envio SMTP: {error}") from error
