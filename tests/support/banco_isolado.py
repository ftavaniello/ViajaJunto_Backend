"""Schemas descartáveis exclusivamente em PostgreSQL com nome terminado em _test."""

import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema

from alembic import command

RAIZ = Path(__file__).resolve().parents[2]


def config_migracao():
    config = Config()
    config.set_main_option("script_location", str(RAIZ / "alembic"))
    return config


def migrar(engine, revisao="head"):
    config = config_migracao()
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, revisao)


@contextmanager
def banco_isolado(revisao="head"):
    url = make_url(os.getenv("TEST_DATABASE_URL") or os.environ["DATABASE_URL"])
    if url.get_backend_name() != "postgresql" or not (url.database or "").endswith("_test"):
        raise ValueError("A validação exige PostgreSQL com nome terminado em _test")
    schema = "validacao31_" + uuid4().hex
    admin = create_engine(url)
    isolado = None
    criado = False
    try:
        with admin.begin() as conn:
            if not conn.scalar(text("SELECT current_database()")).endswith("_test"):
                raise ValueError("O banco conectado não é de testes")
            conn.execute(CreateSchema(schema))
            criado = True
        # Todas as conexões (inclusive as concorrentes) usam o schema próprio.
        isolado = create_engine(url.update_query_dict({"options": f"-csearch_path={schema}"}))
        migrar(isolado, revisao)
        yield isolado
    finally:
        if isolado is not None:
            isolado.dispose()
        if criado:
            with admin.begin() as conn:
                conn.execute(DropSchema(schema, cascade=True))
        admin.dispose()
