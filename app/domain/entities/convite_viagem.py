import hashlib
import secrets
from datetime import datetime, timedelta

from app.domain.regras import CONVITE_VALIDADE_DIAS
from app.domain.validation import validar_email


def normalizar_email(email: str) -> str:
    return email.strip().lower() if isinstance(email, str) else email


class ConviteViagem:
    """Convite por email para entrar em uma viagem (RF18).

    O valor sorteado só existe no link enviado ao convidado; o sistema guarda
    apenas o hash SHA-256 dele. O convite é de uso único e só a conta com o
    email convidado pode aceitá-lo, então repassar o link não dá acesso a outra
    pessoa.
    """

    def __init__(
        self,
        viagem_id: int,
        email: str,
        token_hash: str,
        expira_em: datetime,
        convidado_por_id: int | None = None,
        aceito_em: datetime | None = None,
        id: int | None = None,
        criado_em: datetime | None = None,
    ):
        email = normalizar_email(email)
        validar_email(email)
        self.id = id
        self.viagem_id = viagem_id
        self.email = email
        self.token_hash = token_hash
        self.expira_em = expira_em
        self.convidado_por_id = convidado_por_id
        self.aceito_em = aceito_em
        self.criado_em = criado_em

    @classmethod
    def emitir(
        cls, viagem_id: int, email: str, convidado_por_id: int, agora: datetime
    ) -> tuple["ConviteViagem", str]:
        """Sorteia um token novo; retorna o convite e o valor a enviar por email."""
        # 32 bytes do gerador criptográfico: inviável de adivinhar.
        valor = secrets.token_urlsafe(32)
        convite = cls(
            viagem_id=viagem_id,
            email=email,
            token_hash=cls.calcular_hash(valor),
            expira_em=agora + timedelta(days=CONVITE_VALIDADE_DIAS),
            convidado_por_id=convidado_por_id,
        )
        return convite, valor

    @staticmethod
    def calcular_hash(valor: str) -> str:
        return hashlib.sha256(valor.encode()).hexdigest()

    @property
    def aceito(self) -> bool:
        return self.aceito_em is not None

    def expirado(self, agora: datetime) -> bool:
        return agora >= self.expira_em

    def destinado_a(self, email: str) -> bool:
        return self.email == normalizar_email(email)

    def marcar_aceito(self, agora: datetime) -> None:
        self.aceito_em = agora
