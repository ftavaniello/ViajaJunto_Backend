"""Enriquecimento do catálogo no PostgreSQL, com fornecedor falso (sem rede)."""
import importlib.util
import uuid
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateSchema

from app.adapters.inbound.cli import enriquecer_catalogo as cli
from app.adapters.outbound.locais.provedor_locais_memory import ProvedorLocaisMemory
from app.adapters.outbound.persistence.avaliacao_model import AvaliacaoModel
from app.adapters.outbound.persistence.catalogo_model import CatalogoAtividadeModel
from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.adapters.outbound.persistence.destino_viagem_repository_sqlalchemy import (
    SQLAlchemyDestinoViagemRepository,
)
from app.adapters.outbound.persistence.roteiro_model import AtividadeViagemModel
from app.adapters.outbound.persistence.unit_of_work_sqlalchemy import SQLAlchemyUnitOfWork
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.persistence.viagem_repository_sqlalchemy import (
    SQLAlchemyViagemRepository,
)
from app.application.use_cases.criar_viagem import CriarViagem
from app.domain.entities.catalogo import DestinoCatalogo
from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.entities.usuario import Usuario
from app.domain.enums import CategoriaAtividade, FonteCatalogo
from app.domain.errors import ProvedorLocaisIndisponivel
from app.domain.ports.provedor_locais import LocalExterno
from app.infrastructure.config import carregar_settings
from app.infrastructure.database import get_db
from app.infrastructure.dependencies import montar_enriquecer_catalogo
from app.main import app

PASSEIO = CategoriaAtividade.PASSEIO


def local(nome: str, id_externo: str = "geo-museu") -> LocalExterno:
    return LocalExterno(
        id_externo=id_externo,
        nome=nome,
        latitude=Decimal("28.572447"),
        longitude=Decimal("-81.365295"),
        endereco="2416 N Mills Ave, Orlando",
    )


@pytest.fixture
def client(db_session):
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def orlando(db_session):
    destino = SQLAlchemyCatalogoRepository(db_session).salvar_destino(
        DestinoCatalogo(
            nome="Orlando",
            pais_codigo="US",
            latitude=Decimal("28.538336"),
            longitude=Decimal("-81.379234"),
        )
    )
    db_session.commit()
    return destino


@pytest.fixture
def provedor():
    provedor = ProvedorLocaisMemory()
    provedor.locais[PASSEIO] = [local("Orlando Museum of Art")]
    return provedor


def _usar_em_viagem_e_avaliar(db_session, email_teste, orlando, atividade_id) -> int:
    """Coloca a atividade num roteiro e registra uma avaliação dela."""
    usuario = SQLAlchemyUsuarioRepository(db_session).salvar(
        Usuario(nome="Ana", email=email_teste, senha_hash="hash")
    )
    viagem = CriarViagem(
        SQLAlchemyViagemRepository(db_session), SQLAlchemyUnitOfWork(db_session)
    ).execute(usuario.id, "Flórida", None, date(2027, 7, 1), date(2027, 7, 10))
    parada = SQLAlchemyDestinoViagemRepository(db_session).salvar(
        DestinoViagem(
            viagem_id=viagem.id,
            destino=orlando,
            ordem=1,
            data_chegada=date(2027, 7, 1),
            data_saida=date(2027, 7, 5),
        )
    )
    no_roteiro = AtividadeViagemModel(
        destino_viagem_id=parada.id, catalogo_atividade_id=atividade_id, data=date(2027, 7, 2)
    )
    db_session.add(no_roteiro)
    db_session.flush()
    db_session.add(
        AvaliacaoModel(
            usuario_id=usuario.id,
            catalogo_atividade_id=atividade_id,
            atividade_viagem_id=no_roteiro.id,
            nota=5,
        )
    )
    db_session.commit()
    return no_roteiro.id


def test_atualizar_dados_externos_preserva_avaliacoes_e_roteiros(
    client, db_session, email_teste, orlando, provedor
):
    caso = montar_enriquecer_catalogo(db_session, provedor)
    assert caso.execute(orlando.id, PASSEIO).criadas == 1
    atividade_id = db_session.scalar(select(CatalogoAtividadeModel.id))
    no_roteiro_id = _usar_em_viagem_e_avaliar(db_session, email_teste, orlando, atividade_id)
    provedor.locais[PASSEIO] = [local("Orlando Museum of Art (OMA)")]

    resultado = caso.execute(orlando.id, PASSEIO)

    assert (resultado.criadas, resultado.atualizadas) == (0, 1)
    assert db_session.scalar(select(func.count()).select_from(CatalogoAtividadeModel)) == 1
    assert db_session.get(AtividadeViagemModel, no_roteiro_id).catalogo_atividade_id == (
        atividade_id
    )
    publica = client.get(f"/catalogo/atividades/{atividade_id}").json()
    assert publica["nome"] == "Orlando Museum of Art (OMA)"
    assert publica["fonte"] == "geoapify"
    assert publica["id_externo"] == "geo-museu"
    assert publica["destino"]["fonte"] == "manual"
    assert (publica["media_avaliacoes"], publica["total_avaliacoes"]) == (5.0, 1)


def test_falha_do_fornecedor_nao_grava(db_session, orlando, provedor):
    provedor.falha = ProvedorLocaisIndisponivel("Geoapify indisponível (HTTP 503)")

    with pytest.raises(ProvedorLocaisIndisponivel):
        montar_enriquecer_catalogo(db_session, provedor).execute(orlando.id, PASSEIO)

    assert db_session.scalar(select(func.count()).select_from(CatalogoAtividadeModel)) == 0


def test_banco_impede_duplicar_o_mesmo_local_do_mesmo_fornecedor(db_session, orlando):
    def atividade(fonte: str) -> CatalogoAtividadeModel:
        return CatalogoAtividadeModel(
            destino_catalogo_id=orlando.id,
            nome="Museu",
            categoria="passeio",
            fonte=fonte,
            id_externo="mesmo-id",
        )

    # O mesmo id em fornecedores diferentes não colide.
    db_session.add_all([atividade("geoapify"), atividade("manual")])
    db_session.flush()
    db_session.add(atividade("geoapify"))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_banco_recusa_fonte_desconhecida(db_session, orlando):
    db_session.add(
        CatalogoAtividadeModel(
            destino_catalogo_id=orlando.id, nome="Museu", categoria="passeio", fonte="google"
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


# --- Comando de operador ----------------------------------------------------------


def test_cli_grava_e_resume_o_resultado(db_session, orlando, provedor, monkeypatch, capsys):
    @contextmanager
    def sessao():
        yield db_session

    monkeypatch.setattr(cli, "SessionLocal", sessao)
    monkeypatch.setattr(cli, "criar_provedor_locais", lambda _config: provedor)

    cli.main(["--destino", str(orlando.id), "--categoria", "passeio", "--limite", "5"])

    assert capsys.readouterr().out.strip() == (
        "Catálogo enriquecido: 1 criada(s), 0 atualizada(s), 0 ignorada(s)."
    )
    assert provedor.buscas[0][2:] == (PASSEIO, 5_000, 5)
    assert db_session.scalar(
        select(CatalogoAtividadeModel.fonte).where(CatalogoAtividadeModel.id_externo == "geo-museu")
    ) == FonteCatalogo.GEOAPIFY.value


def test_cli_sem_chave_explica_e_nao_grava(db_session, orlando, monkeypatch, capsys):
    # Ignora uma chave real que esteja no .env de quem roda os testes.
    monkeypatch.setattr(cli, "settings", carregar_settings({}))

    with pytest.raises(SystemExit) as saida:
        cli.main(["--destino", str(orlando.id), "--categoria", "passeio"])

    assert saida.value.code == 2
    assert "Configure GEOAPIFY_API_KEY" in capsys.readouterr().err
    assert db_session.scalar(select(func.count()).select_from(CatalogoAtividadeModel)) == 0


def test_cli_recusa_categoria_desconhecida(capsys):
    with pytest.raises(SystemExit) as saida:
        cli.main(["--destino", "1", "--categoria", "museus"])

    assert saida.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


# --- Migração ---------------------------------------------------------------------


def test_migracao_id_externo_sobe_e_desce_sem_perder_registros(db_session):
    schema = "id_externo_" + uuid.uuid4().hex
    db_session.execute(CreateSchema(schema))
    db_session.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    db_session.execute(
        text(
            "CREATE TABLE destinos_catalogo (id INTEGER PRIMARY KEY, "
            "google_place_id VARCHAR(255), "
            "CONSTRAINT destinos_catalogo_google_place_id_key UNIQUE (google_place_id)); "
            "CREATE TABLE catalogo_atividades (id INTEGER PRIMARY KEY, "
            "fonte VARCHAR(30) NOT NULL DEFAULT 'manual', google_place_id VARCHAR(255), "
            "CONSTRAINT catalogo_atividades_google_place_id_key UNIQUE (google_place_id)); "
            "INSERT INTO destinos_catalogo VALUES (1, 'curado-destino'); "
            "INSERT INTO catalogo_atividades VALUES (1, 'manual', 'curado-atividade')"
        )
    )
    arquivo = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/a7d3e8c25f61_id_externo_catalogo.py"
    )
    spec = importlib.util.spec_from_file_location("migracao_id_externo", arquivo)
    migracao = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migracao)

    with Operations.context(MigrationContext.configure(db_session.connection())):
        migracao.upgrade()
        assert db_session.execute(
            text("SELECT fonte, id_externo FROM destinos_catalogo")
        ).one() == ("manual", "curado-destino")
        db_session.execute(
            text("INSERT INTO catalogo_atividades VALUES (2, 'geoapify', 'curado-atividade')")
        )
        migracao.downgrade()

    linhas = db_session.execute(
        text("SELECT id, fonte, google_place_id FROM catalogo_atividades ORDER BY id")
    ).all()
    # O registro do fornecedor continua existindo (avaliações apontam para ele).
    assert linhas == [(1, "manual", "curado-atividade"), (2, "manual", None)]
    assert db_session.execute(text("SELECT google_place_id FROM destinos_catalogo")).one() == (
        "curado-destino",
    )
