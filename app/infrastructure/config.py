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


settings = Settings()
