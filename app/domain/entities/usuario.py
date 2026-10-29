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
        versao_sessao: int = 0,
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
        # Tokens emitidos com versao diferente da atual sao recusados; incrementar
        # encerra todas as sessoes do usuario (ex.: troca de senha).
        self.versao_sessao = versao_sessao
