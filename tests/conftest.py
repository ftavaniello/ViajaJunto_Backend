import os
import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url

from alembic import command

# O banco de testes precisa ser definido antes de importar `app`, porque config.py e
# database.py leem DATABASE_URL no import. Assim os testes nunca tocam o banco de dev.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://viajajunto:viajajunto@localhost:5433/viajajunto_test",
)
if not (make_url(TEST_DATABASE_URL).database or "").endswith("_test"):
    pytest.exit(
        "TEST_DATABASE_URL deve apontar para um banco cujo nome termina em '_test'; "
        "os testes desfazem gravações e não podem usar o banco de desenvolvimento.",
        returncode=1,
    )
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.infrastructure.database import SessionLocal, engine  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def email_teste() -> str:
    return f"teste-{uuid.uuid4().hex}@example.com"


@pytest.fixture(scope="session")
def banco_de_testes():
    """Exige o PostgreSQL de testes e aplica as migrações uma vez por execução."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as error:
        pytest.fail(
            f"PostgreSQL de testes indisponível em {make_url(TEST_DATABASE_URL)!r}. "
            "Suba com `docker compose --profile test up -d db_test` "
            "ou defina TEST_DATABASE_URL.\n"
            f"Erro: {error}",
            pytrace=False,
        )

    config = Config()
    config.set_main_option("script_location", str(RAIZ / "alembic"))
    command.upgrade(config, "head")


@pytest.fixture
def db_session(banco_de_testes):
    """Session dentro de uma transação externa desfeita ao final de cada teste.

    Os commits feitos pelo código (UnitOfWork, testes) viram SAVEPOINTs, então nada do
    que o teste grava sobrevive a ele.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()
