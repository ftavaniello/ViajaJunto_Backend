from datetime import datetime

from app.domain.errors import DadosInvalidos
from app.domain.validation import validar_email, validar_nome


class Usuario:
    def __init__(
        self,
        nome: str,
        email: str,
        senha_hash: str,
        id: int | None = None,
        criado_em: datetime | None = None,
    ):
        validar_nome(nome)
        validar_email(email)
        if not senha_hash.strip():
            raise DadosInvalidos("Senha n\u00e3o pode ser vazia")

        self.id = id
        self.nome = nome
        self.email = email
        self.senha_hash = senha_hash
        self.criado_em = criado_em
