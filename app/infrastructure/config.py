import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# Ambientes em que a API pode subir com o segredo JWT de exemplo. Qualquer outro
# valor de APP_ENV (production, staging...) exige um segredo proprio.
AMBIENTES_DE_DESENVOLVIMENTO = frozenset({"development", "test"})
JWT_SECRET_KEY_DEV = "changeme-super-secret-key-dev-only"
# HS256 usa chave de 256 bits; segredos menores enfraquecem a assinatura.
JWT_SECRET_KEY_TAMANHO_MINIMO = 32


class ConfiguracaoInvalida(RuntimeError):
    """Configuracao de ambiente insegura ou incompleta; a API nao deve subir."""


@dataclass
class Settings:
    APP_ENV: str
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_EXPIRE_MINUTES: int
    REDIS_URL: str
    REDIS_URL_FILE: str
    CACHE_TTL_SECONDS: int

    @property
    def em_desenvolvimento(self) -> bool:
        return self.APP_ENV in AMBIENTES_DE_DESENVOLVIMENTO


def carregar_settings(env: Mapping[str, str] = os.environ) -> Settings:
    app_env = (env.get("APP_ENV") or "development").strip().lower()
    # Variavel vazia (ex.: "${JWT_SECRET_KEY:-}" no compose) conta como ausente.
    jwt_secret = env.get("JWT_SECRET_KEY") or ""
    if not jwt_secret and app_env in AMBIENTES_DE_DESENVOLVIMENTO:
        jwt_secret = JWT_SECRET_KEY_DEV

    return Settings(
        APP_ENV=app_env,
        DATABASE_URL=env.get(
            "DATABASE_URL",
            "postgresql+psycopg2://viajajunto:viajajunto@localhost:5432/viajajunto",
        ),
        JWT_SECRET_KEY=jwt_secret,
        JWT_ALGORITHM="HS256",
        JWT_EXPIRE_MINUTES=_inteiro(env, "JWT_EXPIRE_MINUTES", 60),
        REDIS_URL=env.get("REDIS_URL", ""),
        REDIS_URL_FILE=env.get("REDIS_URL_FILE", ""),
        CACHE_TTL_SECONDS=max(1, _inteiro(env, "CACHE_TTL_SECONDS", 60)),
    )


def validar_settings(config: Settings) -> None:
    """Falha cedo, na inicializacao, em vez de emitir tokens com segredo fraco.

    As mensagens nunca incluem o valor do segredo, para nao vaza-lo em logs.
    """
    if config.JWT_EXPIRE_MINUTES <= 0:
        raise ConfiguracaoInvalida("JWT_EXPIRE_MINUTES deve ser maior que zero")

    if config.em_desenvolvimento:
        return

    if not config.JWT_SECRET_KEY:
        raise ConfiguracaoInvalida(
            f"JWT_SECRET_KEY é obrigatória quando APP_ENV={config.APP_ENV}"
        )
    if config.JWT_SECRET_KEY == JWT_SECRET_KEY_DEV:
        raise ConfiguracaoInvalida(
            "JWT_SECRET_KEY de desenvolvimento não pode ser usada fora do desenvolvimento"
        )
    if len(config.JWT_SECRET_KEY.encode()) < JWT_SECRET_KEY_TAMANHO_MINIMO:
        raise ConfiguracaoInvalida(
            f"JWT_SECRET_KEY deve ter pelo menos {JWT_SECRET_KEY_TAMANHO_MINIMO} bytes"
        )


def _inteiro(env: Mapping[str, str], nome: str, padrao: int) -> int:
    valor = env.get(nome)
    if valor is None or not valor.strip():
        return padrao
    try:
        return int(valor)
    except ValueError as error:
        raise ConfiguracaoInvalida(f"{nome} deve ser um número inteiro") from error


settings = carregar_settings()
