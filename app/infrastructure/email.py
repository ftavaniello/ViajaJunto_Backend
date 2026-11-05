from app.adapters.outbound.email.console_email_sender import ConsoleEmailSender
from app.adapters.outbound.email.smtp_email_sender import SmtpEmailSender
from app.domain.ports.email_sender import EmailSender
from app.infrastructure.config import Settings, settings


def criar_email_sender(config: Settings) -> EmailSender:
    if config.EMAIL_BACKEND == "smtp":
        return SmtpEmailSender(
            host=config.SMTP_HOST,
            port=config.SMTP_PORT,
            remetente=config.EMAIL_REMETENTE,
            usuario=config.SMTP_USUARIO,
            senha=config.SMTP_SENHA,
            starttls=config.SMTP_STARTTLS,
        )
    if config.EMAIL_BACKEND == "console":
        return ConsoleEmailSender()
    raise ValueError(f"EMAIL_BACKEND desconhecido: {config.EMAIL_BACKEND!r} (use smtp ou console)")


def get_email_sender() -> EmailSender:
    return criar_email_sender(settings)
