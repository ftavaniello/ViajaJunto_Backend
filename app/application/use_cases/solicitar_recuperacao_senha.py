import logging
from collections.abc import Callable
from datetime import datetime, timezone
from urllib.parse import urlencode

from app.domain.entities.token_recuperacao_senha import TokenRecuperacaoSenha
from app.domain.ports.email_sender import EmailSender, FalhaEnvioEmail, MensagemEmail
from app.domain.ports.token_recuperacao_senha_repository import TokenRecuperacaoSenhaRepository
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.usuario_repository import UsuarioRepository
from app.domain.regras import RECUPERACAO_SENHA_VALIDADE_MINUTOS

logger = logging.getLogger(__name__)


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class SolicitarRecuperacaoSenha:
    """Envia por email um link de redefinicao de senha (RF03).

    Nao retorna nada nem levanta erro para email desconhecido ou falha de envio:
    o resultado e sempre o mesmo, para nao revelar quais emails tem conta.
    """

    def __init__(
        self,
        repository: UsuarioRepository,
        tokens: TokenRecuperacaoSenhaRepository,
        email_sender: EmailSender,
        uow: UnitOfWork,
        url_redefinicao: str,
        validade_minutos: int = RECUPERACAO_SENHA_VALIDADE_MINUTOS,
        relogio: Callable[[], datetime] = _agora_utc,
    ):
        self.repository = repository
        self.tokens = tokens
        self.email_sender = email_sender
        self.uow = uow
        self.url_redefinicao = url_redefinicao
        self.validade_minutos = validade_minutos
        self.relogio = relogio

    def execute(self, email: str) -> None:
        usuario = self.repository.buscar_por_email(email)

        if usuario is None:
            return

        agora = self.relogio()
        token, valor = TokenRecuperacaoSenha.emitir(usuario.id, agora, self.validade_minutos)

        with self.uow:
            self.tokens.invalidar_pendentes(usuario.id, agora)
            self.tokens.salvar(token)
            self.uow.commit()

        try:
            self.email_sender.enviar(self._mensagem(usuario.email, valor))
        except FalhaEnvioEmail:
            # O valor do token nao e gravado nem logado: o link que nao chegou fica
            # inutilizavel e o usuario pode pedir outro.
            logger.exception("Falha ao enviar email de recuperacao do usuario %s", usuario.id)

    def _mensagem(self, destinatario: str, valor: str) -> MensagemEmail:
        link = f"{self.url_redefinicao}?{urlencode({'token': valor})}"
        corpo = (
            "Recebemos um pedido para redefinir a senha da sua conta no ViajaJunto.\n\n"
            f"Para escolher uma nova senha, acesse:\n{link}\n\n"
            f"Se preferir, informe este código na tela de redefinição:\n{valor}\n\n"
            f"O link vale por {self.validade_minutos} minutos e só pode ser usado uma vez. "
            "Se você não fez este pedido, ignore este email: sua senha continua a mesma."
        )
        return MensagemEmail(
            destinatario=destinatario,
            assunto="Redefinição de senha - ViajaJunto",
            corpo=corpo,
        )
