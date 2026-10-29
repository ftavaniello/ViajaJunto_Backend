"""Adaptadores de envio de email e escolha por configuracao (EMAIL_BACKEND)."""
import logging
import smtplib
from unittest.mock import MagicMock

import pytest

from app.adapters.outbound.email.console_email_sender import ConsoleEmailSender
from app.adapters.outbound.email.smtp_email_sender import SmtpEmailSender
from app.domain.ports.email_sender import FalhaEnvioEmail, MensagemEmail
from app.infrastructure.config import Settings
from app.infrastructure.email import criar_email_sender

MENSAGEM = MensagemEmail(destinatario="livia@example.com", assunto="Assunto", corpo="Corpo")


def _smtp_falso(monkeypatch) -> MagicMock:
    smtp = MagicMock()
    classe = MagicMock(return_value=smtp)
    smtp.__enter__.return_value = smtp
    monkeypatch.setattr(smtplib, "SMTP", classe)
    return classe


def test_smtp_envia_mensagem_com_remetente_destinatario_e_assunto(monkeypatch):
    classe = _smtp_falso(monkeypatch)

    SmtpEmailSender("mailpit", 1025, "ViajaJunto <nao-responda@viajajunto.local>").enviar(
        MENSAGEM
    )

    classe.assert_called_once_with("mailpit", 1025, timeout=10)
    smtp = classe.return_value
    smtp.starttls.assert_not_called()
    smtp.login.assert_not_called()
    [enviado] = smtp.send_message.call_args.args
    assert enviado["From"] == "ViajaJunto <nao-responda@viajajunto.local>"
    assert enviado["To"] == "livia@example.com"
    assert enviado["Subject"] == "Assunto"
    assert enviado.get_content().strip() == "Corpo"


def test_smtp_com_starttls_e_autenticacao(monkeypatch):
    classe = _smtp_falso(monkeypatch)

    SmtpEmailSender(
        "smtp.exemplo.com", 587, "x@exemplo.com", usuario="u", senha="s", starttls=True
    ).enviar(MENSAGEM)

    smtp = classe.return_value
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("u", "s")


@pytest.mark.parametrize(
    "erro", [ConnectionRefusedError("recusado"), smtplib.SMTPRecipientsRefused({})]
)
def test_smtp_converte_falhas_em_falha_envio_email(monkeypatch, erro):
    classe = _smtp_falso(monkeypatch)
    classe.side_effect = erro

    with pytest.raises(FalhaEnvioEmail):
        SmtpEmailSender("mailpit", 1025, "x@exemplo.com").enviar(MENSAGEM)


def test_smtp_sem_servidor_real_levanta_falha_envio_email():
    # Porta 1 no localhost: conexao recusada de verdade, sem mock.
    with pytest.raises(FalhaEnvioEmail):
        SmtpEmailSender("127.0.0.1", 1, "x@exemplo.com", timeout=1).enviar(MENSAGEM)


def test_console_escreve_o_email_no_log(caplog):
    with caplog.at_level(logging.WARNING):
        ConsoleEmailSender().enviar(MENSAGEM)

    assert "livia@example.com" in caplog.text
    assert "Corpo" in caplog.text


def _config(**valores) -> Settings:
    config = Settings()
    for nome, valor in valores.items():
        setattr(config, nome, valor)
    return config


def test_configuracao_escolhe_o_adaptador():
    assert isinstance(criar_email_sender(_config(EMAIL_BACKEND="console")), ConsoleEmailSender)

    smtp = criar_email_sender(
        _config(EMAIL_BACKEND="smtp", SMTP_HOST="mailpit", SMTP_PORT=1025, SMTP_STARTTLS=True)
    )
    assert isinstance(smtp, SmtpEmailSender)
    assert (smtp.host, smtp.port, smtp.starttls) == ("mailpit", 1025, True)


def test_configuracao_desconhecida_e_recusada():
    with pytest.raises(ValueError, match="EMAIL_BACKEND"):
        criar_email_sender(_config(EMAIL_BACKEND="pombo-correio"))
