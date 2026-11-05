from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Barrier
from uuid import uuid4

from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from alembic import command
from app.adapters.outbound.persistence.avaliacao_model import AvaliacaoModel
from app.adapters.outbound.persistence.avaliacao_repository_sqlalchemy import (
    SQLAlchemyAvaliacaoRepository,
)
from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.adapters.outbound.persistence.roteiro_model import AtividadeViagemModel, DestinoViagemModel
from app.adapters.outbound.persistence.unit_of_work_sqlalchemy import SQLAlchemyUnitOfWork
from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.adapters.outbound.persistence.viagem_repository_sqlalchemy import (
    SQLAlchemyViagemRepository,
)
from app.application.use_cases.criar_viagem import CriarViagem
from app.domain.entities.avaliacao import Avaliacao
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.infrastructure.config import settings
from app.infrastructure.database import engine


def test_upsert_concorrente_nao_duplica_avaliacao(banco_de_testes, monkeypatch):
    # Schema descartável, somente no PostgreSQL exclusivo dos testes.
    schema = "concorrencia_review_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    url = make_url(settings.DATABASE_URL).update_query_dict({"options": f"-csearch_path={schema}"})
    isolado = create_engine(url)
    monkeypatch.setattr(settings, "DATABASE_URL", url.render_as_string(hide_password=False))
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "alembic"))
    try:
        command.upgrade(config, "head")
        with Session(isolado) as db:
            usuario = UsuarioModel(nome="Autor", email="autor@example.com", senha_hash="hash")
            db.add(usuario)
            db.flush()
            usuario_id = usuario.id
            catalogo = SQLAlchemyCatalogoRepository(db)
            destino = catalogo.salvar_destino(DestinoCatalogo(nome="Lisboa", pais_codigo="PT"))
            atividade = catalogo.salvar_atividade(
                AtividadeCatalogo(destino=destino, nome="Museu", categoria="passeio")
            )
            viagem = CriarViagem(SQLAlchemyViagemRepository(db), SQLAlchemyUnitOfWork(db)).execute(
                usuario_id,
                "Viagem",
                None,
                date(2027, 1, 1),
                date(2027, 1, 10),
            )
            parada = DestinoViagemModel(
                viagem_id=viagem.id,
                destino_catalogo_id=destino.id,
                ordem=1,
                data_chegada=date(2027, 1, 1),
                data_saida=date(2027, 1, 10),
            )
            db.add(parada)
            db.flush()
            ocorrencia = AtividadeViagemModel(
                destino_viagem_id=parada.id,
                catalogo_atividade_id=atividade.id,
                data=date(2027, 1, 2),
                status="concluida",
                realizada_em=datetime.now(timezone.utc),
                realizada_por_id=usuario_id,
            )
            db.add(ocorrencia)
            db.flush()
            atividade_id, ocorrencia_id = atividade.id, ocorrencia.id
            db.commit()
        barreira = Barrier(2)

        def publicar(nota):
            with Session(isolado) as db:
                db.execute(text("SET LOCAL statement_timeout = '10s'"))
                barreira.wait(timeout=10)
                review = SQLAlchemyAvaliacaoRepository(db).salvar(
                    Avaliacao(
                        usuario_id=usuario_id,
                        catalogo_atividade_id=atividade_id,
                        atividade_viagem_id=ocorrencia_id,
                        nota=nota,
                    )
                )
                db.commit()
                return review.id

        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(publicar, (1, 5)))
        assert ids[0] == ids[1]
        with Session(isolado) as db:
            assert db.scalar(select(func.count()).select_from(AvaliacaoModel)) == 1
            nota = db.scalar(select(AvaliacaoModel.nota))
            assert nota in (1, 5)
            assert (
                SQLAlchemyCatalogoRepository(db).buscar_atividade(atividade_id).media_avaliacoes
                == nota
            )
    finally:
        isolado.dispose()
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
