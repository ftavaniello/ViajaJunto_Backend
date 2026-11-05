"""Operação administrativa explícita para o PostgreSQL local do Compose."""

from datetime import date
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.pool import NullPool

from alembic import command
from app.infrastructure.config import Settings
from app.infrastructure.seed_demonstracao import executar_seed_completo


def validar_destino_reset(config: Settings, confirmar: bool) -> None:
    if confirmar is not True:
        raise PermissionError("Reset exige a opção --confirmar; nenhum dado foi alterado")
    if config.APP_ENV != "development":
        raise PermissionError("Reset permitido somente em APP_ENV=development")
    url = make_url(config.DATABASE_URL)
    if (
        url.drivername != "postgresql+psycopg2"
        or url.host != "db"
        or url.port != 5432
        or url.database != "viajajunto"
        or url.query
    ):
        raise PermissionError(
            "Reset restrito ao PostgreSQL local do Compose: db:5432/viajajunto, "
            "sem parâmetros extras na conexão"
        )


def resetar_banco(config: Settings, confirmar: bool = False) -> dict:
    validar_destino_reset(config, confirmar)
    banco = create_engine(config.DATABASE_URL, poolclass=NullPool)
    try:
        with banco.begin() as connection:
            if connection.scalar(text("SELECT current_database()")) != "viajajunto":
                raise PermissionError("Banco conectado não corresponde ao destino permitido")
            return _recriar_schema(connection, config, date.today())
    finally:
        banco.dispose()


def _recriar_schema(connection: Connection, config: Settings, referencia: date) -> dict:
    # Chamado somente após validar destino; testes usam uma transação isolada no banco _test.
    connection.execute(text("SET LOCAL lock_timeout = '5s'"))
    connection.execute(text("SET LOCAL statement_timeout = '60s'"))
    connection.execute(text("SELECT pg_advisory_xact_lock(202647, 1)"))
    connection.execute(text("DROP SCHEMA public CASCADE"))
    connection.execute(text("CREATE SCHEMA public"))
    migracoes = Config()
    migracoes.set_main_option(
        "script_location", str(Path(__file__).resolve().parents[2] / "alembic")
    )
    migracoes.attributes["connection"] = connection
    command.upgrade(migracoes, "head")
    _, manifesto = executar_seed_completo(config, connection, referencia)
    return manifesto
