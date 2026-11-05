import hashlib
import secrets
from datetime import datetime, timedelta


class TokenRecuperacaoSenha:
    """Token de uso único para redefinir a senha por email (RF03).

    O valor sorteado só existe no link enviado ao usuário; o sistema guarda apenas
    o hash SHA-256 dele. Quem lê o banco não consegue montar um link válido.
    """

    def __init__(
        self,
        usuario_id: int,
        token_hash: str,
        expira_em: datetime,
        usado_em: datetime | None = None,
        id: int | None = None,
    ):
        self.id = id
        self.usuario_id = usuario_id
        self.token_hash = token_hash
        self.expira_em = expira_em
        self.usado_em = usado_em

    @classmethod
    def emitir(
        cls, usuario_id: int, agora: datetime, validade_minutos: int
    ) -> tuple["TokenRecuperacaoSenha", str]:
        """Sorteia um token novo; retorna a entidade e o valor a enviar por email."""
        # 32 bytes do gerador criptográfico: imprevisível e inviável de adivinhar.
        valor = secrets.token_urlsafe(32)
        token = cls(
            usuario_id=usuario_id,
            token_hash=cls.calcular_hash(valor),
            expira_em=agora + timedelta(minutes=validade_minutos),
        )
        return token, valor

    @staticmethod
    def calcular_hash(valor: str) -> str:
        return hashlib.sha256(valor.encode()).hexdigest()

    def pode_ser_usado(self, agora: datetime) -> bool:
        return self.usado_em is None and agora < self.expira_em

    def marcar_usado(self, agora: datetime) -> None:
        self.usado_em = agora
