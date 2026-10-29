import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://viajajunto:viajajunto@localhost:5432/viajajunto",
    )
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "changeme-super-secret-key-dev-only",
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    REDIS_URL_FILE: str = os.getenv("REDIS_URL_FILE", "")
    CACHE_TTL_SECONDS: int = max(1, int(os.getenv("CACHE_TTL_SECONDS", "60")))
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    # Envio de email: "console" (escreve no log, so dev) ou "smtp".
    EMAIL_BACKEND: str = os.getenv("EMAIL_BACKEND", "console").strip().lower()
    EMAIL_REMETENTE: str = os.getenv(
        "EMAIL_REMETENTE", "ViajaJunto <nao-responda@viajajunto.local>"
    )
    SMTP_HOST: str = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "1025"))
    SMTP_USUARIO: str = os.getenv("SMTP_USUARIO", "")
    SMTP_SENHA: str = os.getenv("SMTP_SENHA", "")
    SMTP_STARTTLS: bool = os.getenv("SMTP_STARTTLS", "false").strip().lower() == "true"
    # Pagina do frontend que recebe ?token=... e pede a nova senha.
    RECUPERACAO_SENHA_URL: str = os.getenv(
        "RECUPERACAO_SENHA_URL", "http://localhost:3000/redefinir-senha"
    )


settings = Settings()
