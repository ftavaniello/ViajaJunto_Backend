import importlib.util
import uuid
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.schema import CreateSchema


def test_migracao_destinos_preserva_registro_existente_e_downgrade(db_session):
    # Schema isolado no banco exclusivo de testes; o rollback da fixture o remove.
    schema = "migracao_destinos_" + uuid.uuid4().hex
    db_session.execute(CreateSchema(schema))
    db_session.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    db_session.execute(
        text(
            "CREATE TABLE destinos_catalogo (id INTEGER PRIMARY KEY, nome VARCHAR(255), "
            "pais_codigo VARCHAR(2), foto_url VARCHAR(500))"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO destinos_catalogo (id, nome, pais_codigo, foto_url) "
            "VALUES (1, 'Lisboa', 'PT', 'https://example.com/foto.jpg')"
        )
    )
    caminho = Path(__file__).resolve().parents[2] / (
        "alembic/versions/a4d9e2f61b80_categoria_descricao_destinos.py"
    )
    spec = importlib.util.spec_from_file_location("migracao_destinos", caminho)
    migracao = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migracao)
    contexto = MigrationContext.configure(db_session.connection())
    with Operations.context(contexto):
        migracao.upgrade()
        registro = db_session.execute(
            text("SELECT nome, pais_codigo, foto_url, categoria, descricao FROM destinos_catalogo")
        ).one()
        assert tuple(registro) == ("Lisboa", "PT", "https://example.com/foto.jpg", "cidade", None)
        migracao.downgrade()
        registro = db_session.execute(
            text("SELECT nome, pais_codigo, foto_url FROM destinos_catalogo")
        ).one()
        assert tuple(registro) == ("Lisboa", "PT", "https://example.com/foto.jpg")
