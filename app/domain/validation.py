import re

from app.domain.errors import DadosInvalidos


def validar_nome(nome: str) -> None:
    if not isinstance(nome, str) or not nome.strip():
        raise DadosInvalidos("Nome não pode ser vazio")


def validar_email(email: str) -> None:
    # Regra basica do dominio; o adaptador HTTP tambem verifica o formato detalhado.
    if not isinstance(email, str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise DadosInvalidos("Email inválido")


def validar_senha(senha: str) -> None:
    if not isinstance(senha, str) or len(senha) < 8:
        raise DadosInvalidos("Senha deve conter pelo menos 8 caracteres")
