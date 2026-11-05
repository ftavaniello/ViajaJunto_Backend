import importlib.util
import uuid
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema

from alembic import command
from app.infrastructure.config import settings
from app.infrastructure.database import engine


def test_migracao_status_preserva_custo_comprovacao_e_cancelamento(db_session):
    schema = "status_atividade_" + uuid.uuid4().hex
    db_session.execute(CreateSchema(schema))
    db_session.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    db_session.execute(
        text(
            "CREATE TABLE atividades_viagem (id INTEGER PRIMARY KEY, "
            "status VARCHAR(20) NOT NULL DEFAULT 'planejada', "
            "realizada_em TIMESTAMPTZ, custo_previsto NUMERIC(12,2) NOT NULL DEFAULT 0, "
            "CONSTRAINT ck_atividades_viagem_status "
            "CHECK (status IN ('planejada','realizada','cancelada')), "
            "CONSTRAINT ck_atividades_viagem_comprovacao "
            "CHECK (status <> 'realizada' OR realizada_em IS NOT NULL))"
        )
    )
    db_session.execute(
        text(
            "INSERT INTO atividades_viagem (id,status,realizada_em,custo_previsto) VALUES "
            "(1,'planejada',NULL,0.10), (2,'realizada','2026-10-31T12:00:00Z',15.25), "
            "(3,'cancelada',NULL,20.30)"
        )
    )
    arquivo = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/b5e0f3a72c91_status_atividade_rf13.py"
    )
    spec = importlib.util.spec_from_file_location("migracao_status_atividade", arquivo)
    migracao = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migracao)
    consulta = text(
        "SELECT id,status,realizada_em,custo_previsto FROM atividades_viagem ORDER BY id"
    )
    antes = list(db_session.execute(consulta))
    with Operations.context(MigrationContext.configure(db_session.connection())):
        migracao.upgrade()
        depois = list(db_session.execute(consulta))
        assert [r.status for r in depois] == ["pendente", "concluida", "cancelada"]
        assert [r.custo_previsto for r in depois] == [r.custo_previsto for r in antes]
        assert depois[1].realizada_em == antes[1].realizada_em
        db_session.execute(
            text("INSERT INTO atividades_viagem (id,status) VALUES (4,'confirmada')")
        )
        migracao.downgrade()
        estados = list(db_session.scalars(text("SELECT status FROM atividades_viagem ORDER BY id")))
        assert estados == ["planejada", "realizada", "cancelada", "planejada"]


def test_historico_completo_em_schema_vazio_tem_uma_ponta(banco_de_testes, monkeypatch):
    # Mesmo PostgreSQL exclusivo de testes, em schema descartável e sem tocar no público.
    schema = "historico_atividades_" + uuid.uuid4().hex
    with engine.begin() as conexao:
        conexao.execute(CreateSchema(schema))
    url = make_url(settings.DATABASE_URL).update_query_dict({"options": f"-csearch_path={schema}"})
    isolado = create_engine(url)
    monkeypatch.setattr(settings, "DATABASE_URL", url.render_as_string(hide_password=False))
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "alembic"))
    try:
        command.upgrade(config, "head")
        with isolado.connect() as conexao:
            assert (
                conexao.scalar(text("SELECT version_num FROM alembic_version"))
                == ScriptDirectory.from_config(config).get_current_head()
            )
            assert (
                conexao.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.columns "
                        "WHERE table_schema = :schema AND table_name = 'usuarios' "
                        "AND column_name = 'criado_em'"
                    ),
                    {"schema": schema},
                )
                == 1
            )
        command.downgrade(config, "base")
        with isolado.connect() as conexao:
            assert (
                conexao.scalar(
                    text(
                        "SELECT count(*) FROM information_schema.tables "
                        "WHERE table_schema = :schema AND table_name = 'usuarios'"
                    ),
                    {"schema": schema},
                )
                == 0
            )
    finally:
        isolado.dispose()
        with engine.begin() as conexao:
            conexao.execute(DropSchema(schema, cascade=True))
