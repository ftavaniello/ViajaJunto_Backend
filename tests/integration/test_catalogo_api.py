import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.adapters.inbound.cli.importar_catalogo import importar_arquivo
from app.adapters.outbound.persistence.catalogo_model import (
    CatalogoAtividadeModel,
    DestinoCatalogoModel,
)
from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.adapters.outbound.persistence.unit_of_work_sqlalchemy import SQLAlchemyUnitOfWork
from app.application.use_cases.importar_catalogo import ImportarCatalogo, LoteCatalogo
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.errors import DadosInvalidos
from app.infrastructure.database import get_db
from app.main import app


@pytest.fixture
def client(db_session):
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def catalogo(db_session):
    repo = SQLAlchemyCatalogoRepository(db_session)
    lisboa = repo.salvar_destino(DestinoCatalogo(nome="Lisboa", pais_codigo="PT"))
    porto = repo.salvar_destino(DestinoCatalogo(nome="Porto", pais_codigo="PT"))
    atividades = []
    for nome, categoria, destino, endereco in [
        ("Museu Nacional", "cultura", lisboa, "Rua Azul"),
        ("Museu do Porto", "cultura", porto, None),
        ("Restaurante", "alimentacao", lisboa, "Rua Verde"),
        ("Passeio 100%", "lazer", lisboa, None),
    ]:
        atividades.append(
            repo.salvar_atividade(
                AtividadeCatalogo(
                    destino=destino,
                    nome=nome,
                    categoria=categoria,
                    endereco=endereco,
                    descricao="Descrição pública",
                    foto_url="https://example.com/foto.jpg",
                )
            )
        )
    return atividades


def test_detalhe_publico_sem_token_e_sem_dados_privados(client, catalogo):
    response = client.get(f"/catalogo/atividades/{catalogo[0].id}")
    assert response.status_code == 200
    body = response.json()
    assert body["nome"] == "Museu Nacional"
    assert body["destino"]["nome"] == "Lisboa"
    assert body["foto_url"] == "https://example.com/foto.jpg"
    assert body["fonte"] == "manual"
    assert body["avaliacoes_disponiveis"] is False
    assert body["media_avaliacoes"] is None
    assert body["total_avaliacoes"] is None
    assert body["reviews"] == []
    assert set(body) == {
        "id",
        "nome",
        "descricao",
        "categoria",
        "endereco",
        "latitude",
        "longitude",
        "foto_url",
        "google_place_id",
        "fonte",
        "destino",
        "avaliacoes_disponiveis",
        "media_avaliacoes",
        "total_avaliacoes",
        "reviews",
    }
    assert set(body["destino"]) == {
        "id",
        "nome",
        "pais_codigo",
        "latitude",
        "longitude",
        "foto_url",
        "google_place_id",
    }


@pytest.mark.parametrize(
    ("filtros", "nomes"),
    [
        ({"nome": "MUSEU"}, ["Museu Nacional", "Museu do Porto"]),
        ({"categoria": "alimentacao"}, ["Restaurante"]),
        ({"nome": "museu", "categoria": "cultura", "localizacao": "LISBOA"}, ["Museu Nacional"]),
        ({"localizacao": "azul"}, ["Museu Nacional"]),
        (
            {"localizacao": "pt"},
            ["Museu Nacional", "Museu do Porto", "Restaurante", "Passeio 100%"],
        ),
        ({"nome": "%"}, ["Passeio 100%"]),
        ({"nome": "_"}, []),
        ({"nome": "' OR 1=1 --"}, []),
        ({"nome": "não existe"}, []),
    ],
)
def test_filtros_publicos(client, catalogo, filtros, nomes):
    response = client.get("/catalogo/atividades", params=filtros)
    assert response.status_code == 200
    assert [a["nome"] for a in response.json()["itens"]] == nomes


def test_paginas_e_destino(client, catalogo):
    paginas = [
        client.get(
            "/catalogo/atividades",
            params={
                "pagina": p,
                "tamanho_pagina": 2,
            },
        ).json()
        for p in (1, 2, 3)
    ]
    assert [a["id"] for p in paginas for a in p["itens"]] == [a.id for a in catalogo]
    assert [p["tem_proxima"] for p in paginas] == [True, False, False]
    response = client.get(
        "/catalogo/atividades",
        params={
            "destino_catalogo_id": catalogo[1].destino.id,
        },
    )
    assert [a["id"] for a in response.json()["itens"]] == [catalogo[1].id]


def test_catalogo_vazio_e_detalhe_inexistente(client):
    assert client.get("/catalogo/atividades").json() == {
        "itens": [],
        "pagina": 1,
        "tamanho_pagina": 20,
        "tem_proxima": False,
    }
    assert client.get("/catalogo/atividades/99999999").status_code == 404


@pytest.mark.parametrize(
    "filtros",
    [
        {"pagina": 0},
        {"pagina": "abc"},
        {"tamanho_pagina": 101},
        {"tamanho_pagina": 0},
        {"categoria": "hotel"},
        {"destino_catalogo_id": -1},
        {"nota_minima": 4},
    ],
)
def test_contrato_rejeita_parametros_invalidos(client, filtros):
    assert client.get("/catalogo/atividades", params=filtros).status_code == 422


def test_catalogo_nao_tem_escrita_publica(client):
    assert client.post("/catalogo/atividades", json={"nome": "Injetada"}).status_code == 405
    assert client.delete("/catalogo/atividades/1").status_code == 405
    assert client.patch("/catalogo/atividades/1", json={}).status_code == 405


def test_importacao_json_persiste_e_aparece_publicamente(client, db_session, tmp_path):
    arquivo = tmp_path / "lote.json"
    arquivo.write_text(
        json.dumps(
            {
                "destinos": {"lisboa": {"nome": "Lisboa", "pais_codigo": "PT"}},
                "atividades": [
                    {
                        "destino": "lisboa",
                        "nome": "Museu",
                        "categoria": "cultura",
                        "google_place_id": "referencia-curada",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    caso = ImportarCatalogo(
        SQLAlchemyCatalogoRepository(db_session),
        SQLAlchemyUnitOfWork(db_session),
    )
    assert importar_arquivo(arquivo, caso) == 1
    item = client.get("/catalogo/atividades").json()["itens"][0]
    assert item["google_place_id"] == "referencia-curada"
    assert item["fonte"] == "manual"


def test_importacao_desfaz_lote_inteiro_em_duplicacao(db_session):
    destino = DestinoCatalogo(nome="Lisboa", pais_codigo="PT")
    atividade = AtividadeCatalogo(
        destino=destino, nome="Museu", categoria="cultura", google_place_id="duplicada"
    )
    caso = ImportarCatalogo(
        SQLAlchemyCatalogoRepository(db_session),
        SQLAlchemyUnitOfWork(db_session),
    )
    with pytest.raises(IntegrityError):
        caso.execute(
            LoteCatalogo(
                {"lisboa": destino},
                [
                    ("lisboa", atividade),
                    ("lisboa", replace(atividade, nome="Outra")),
                ],
            )
        )
    assert db_session.scalar(select(func.count()).select_from(CatalogoAtividadeModel)) == 0
    assert db_session.scalar(select(func.count()).select_from(DestinoCatalogoModel)) == 0


def test_importacao_rejeita_json_invalido_sem_gravar(db_session, tmp_path):
    arquivo = tmp_path / "lote.json"
    arquivo.write_text(
        json.dumps(
            {
                "destinos": {"lisboa": {"nome": "Lisboa", "pais_codigo": "PT"}},
                "atividades": [{"destino": "lisboa", "nome": " ", "categoria": "cultura"}],
            }
        ),
        encoding="utf-8",
    )
    caso = ImportarCatalogo(
        SQLAlchemyCatalogoRepository(db_session),
        SQLAlchemyUnitOfWork(db_session),
    )
    with pytest.raises(DadosInvalidos):
        importar_arquivo(arquivo, caso)
    assert db_session.scalar(select(func.count()).select_from(DestinoCatalogoModel)) == 0


def test_openapi_documenta_consulta_publica():
    schema = app.openapi()
    for path in ("/catalogo/atividades", "/catalogo/atividades/{atividade_id}"):
        assert not schema["paths"][path]["get"].get("security")
    assert "ReviewCatalogoResponse" in schema["components"]["schemas"]


def test_seed_do_exemplo_e_reexecucao_preservam_dados(db_session, client):
    from pathlib import Path

    arquivo = Path(__file__).resolve().parents[2] / "docs/catalogo-exemplo.json"
    caso = ImportarCatalogo(
        SQLAlchemyCatalogoRepository(db_session),
        SQLAlchemyUnitOfWork(db_session),
    )
    assert importar_arquivo(arquivo, caso, apenas_se_vazio=True) == 2
    item = db_session.scalar(select(CatalogoAtividadeModel).order_by(CatalogoAtividadeModel.id))
    item.descricao = "Texto editado pela equipe"
    db_session.flush()
    primeira_resposta = client.get("/catalogo/atividades").json()

    assert importar_arquivo(arquivo, caso, apenas_se_vazio=True) == 0
    assert client.get("/catalogo/atividades").json() == primeira_resposta
    assert db_session.scalar(select(func.count()).select_from(DestinoCatalogoModel)) == 1
    assert db_session.scalar(select(func.count()).select_from(CatalogoAtividadeModel)) == 2
    assert item.descricao == "Texto editado pela equipe"


def test_seed_preserva_catalogo_ja_abastecido(db_session, catalogo):
    from pathlib import Path

    caso = ImportarCatalogo(
        SQLAlchemyCatalogoRepository(db_session),
        SQLAlchemyUnitOfWork(db_session),
    )
    arquivo = Path(__file__).resolve().parents[2] / "docs/catalogo-exemplo.json"
    assert importar_arquivo(arquivo, caso, apenas_se_vazio=True) == 0
    assert db_session.scalar(select(func.count()).select_from(CatalogoAtividadeModel)) == len(
        catalogo
    )


def test_reserva_do_seed_serializa_conexoes(db_session):
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    from app.infrastructure.database import SessionLocal

    assert SQLAlchemyCatalogoRepository(db_session).reservar_carga_inicial() is True
    with SessionLocal() as concorrente:
        concorrente.execute(text("SET LOCAL lock_timeout = '200ms'"))
        with pytest.raises(OperationalError):
            SQLAlchemyCatalogoRepository(concorrente).reservar_carga_inicial()
