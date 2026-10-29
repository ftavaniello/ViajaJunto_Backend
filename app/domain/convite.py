import secrets
from datetime import datetime, timedelta

from app.domain.regras import (
    CODIGO_CONVITE_ALFABETO,
    CODIGO_CONVITE_TAMANHO,
    CODIGO_CONVITE_VALIDADE_DIAS,
)


def gerar_codigo_convite() -> str:
    # secrets em vez de random: o codigo da acesso a viagem e nao pode ser previsivel.
    return "".join(secrets.choice(CODIGO_CONVITE_ALFABETO) for _ in range(CODIGO_CONVITE_TAMANHO))


def expiracao_convite(agora: datetime) -> datetime:
    return agora + timedelta(days=CODIGO_CONVITE_VALIDADE_DIAS)
