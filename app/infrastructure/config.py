import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://viajajunto:viajajunto@localhost:5432/viajajunto",
    )


settings = Settings()
