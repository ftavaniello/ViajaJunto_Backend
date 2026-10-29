from enum import StrEnum

from sqlalchemy import CheckConstraint


def check_in(nome: str, coluna: str, enum: type[StrEnum]) -> CheckConstraint:
    """CHECK (coluna IN (...)) com os valores do enum do domínio.

    Colunas texto + CHECK em vez de ENUM nativo do PostgreSQL: acrescentar um
    valor vira uma migração simples, sem `ALTER TYPE`.
    """
    valores = ", ".join(f"'{item.value}'" for item in enum)
    return CheckConstraint(f"{coluna} IN ({valores})", name=nome)
