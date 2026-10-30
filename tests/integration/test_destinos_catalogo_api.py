import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.adapters.inbound.cli.importar_catalogo import importar_json
from app.adapters.outbound.persistence.catalogo_model import DestinoCatalogoModel
from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.adapters.outbound.persistence.unit_of_work_sqlalchemy import SQLAlchemyUnitOfWork
from app.application.use_cases.importar_catalogo import ImportarCatalogo
from app.domain.entities.catalogo import DestinoCatalogo
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
def destinos(db_session):
    repo = SQLAlchemyCatalogoRepository(db_session)
    return [
        repo.salvar_destino(
            DestinoCatalogo(
                nome=nome,
                pais_codigo=pais,
                categoria=categoria,
                descricao="Descrição pública",
                foto_url="https://example.com/destino.jpg",
            )
        )
        for nome, pais, categoria in [
            ("Lisboa", "PT", "cidade"),
            ("Porto", "PT", "cultural"),
            ("Florianópolis", "BR", "praia"),
            ("Serra 100%", "BR", "natureza"),
        ]
    ]


def test_detalhe_publico_destino(client, destinos):
    response = client.get(f"/catalogo/destinos/{destinos[0].id}")
    assert response.status_code == 200
    body = response.json()
    assert body["nome"] == "Lisboa"
    assert body["categoria"] == "cidade"
    assert body["descricao"] == "Descrição pública"
    assert body["foto_url"] == "https://example.com/destino.jpg"
    assert set(body) == {
        "id",
        "nome",
        "pais_codigo",
        "categoria",
        "descricao",
        "latitude",
        "longitude",
        "foto_url",
        "google_place_id",
    }


@pytest.mark.parametrize(
    ("filtros", "esperados"),
    [
        ({"nome": "LISBOA"}, ["Lisboa"]),
        ({"pais_codigo": "pt"}, ["Lisboa", "Porto"]),
        ({"categoria": "praia"}, ["Florianópolis"]),
        ({"nome": "serra", "categoria": "natureza", "pais_codigo": "BR"}, ["Serra 100%"]),
        ({"nome": "%"}, ["Serra 100%"]),
        ({"nome": "_"}, []),
        ({"nome": "' OR 1=1 --"}, []),
        ({"nome": "ausente"}, []),
    ],
)
def test_filtros_destinos_postgresql(client, destinos, filtros, esperados):
    response = client.get("/catalogo/destinos", params=filtros)
    assert response.status_code == 200
    obtidos = [d["nome"] for d in response.json()["itens"]]
    assert obtidos == esperados


def test_paginas_destinos_postgresql(client, destinos):
    paginas = [
        client.get(
            "/catalogo/destinos",
            params={
                "pagina": p,
                "tamanho_pagina": 2,
            },
        ).json()
        for p in (1, 2, 3)
    ]
    ids = [d["id"] for p in paginas for d in p["itens"]]
    esperados = [d.id for d in destinos]
    assert ids == esperados
    assert [p["tem_proxima"] for p in paginas] == [True, False, False]
    assert paginas[-1]["itens"] == []


def test_sem_destinos_e_inexistente(client):
    assert client.get("/catalogo/destinos").json() == {
        "itens": [],
        "pagina": 1,
        "tamanho_pagina": 20,
        "tem_proxima": False,
    }
    assert client.get("/catalogo/destinos/999999999").status_code == 404
    assert client.get("/catalogo/destinos/0").status_code == 422


@pytest.mark.parametrize(
    "filtros",
    [
        {"pagina": 0},
        {"pagina": "abc"},
        {"tamanho_pagina": 101},
        {"categoria": "hotel"},
        {"pais_codigo": "BRA"},
        {"pais_codigo": "12"},
        {"usuario_id": 1},
        {"nome": "x" * 256},
    ],
)
def test_filtros_invalidos_destinos(client, filtros):
    assert client.get("/catalogo/destinos", params=filtros).status_code == 422


def test_sem_escrita_publica_destinos(client):
    assert client.post("/catalogo/destinos", json={}).status_code == 405
    assert client.patch("/catalogo/destinos/1", json={}).status_code == 405
    assert client.delete("/catalogo/destinos/1").status_code == 405


def test_lote_so_destinos_publicado_sem_atividades(client, db_session):
    conteudo = json.dumps(
        {
            "destinos": {
                "praia": {
                    "nome": "Praia",
                    "pais_codigo": "BR",
                    "categoria": "praia",
                    "descricao": "Descrição curada",
                    "latitude": "-27.5",
                    "longitude": "-48.5",
                    "foto_url": "https://example.com/praia.jpg",
                    "google_place_id": "referencia-curada",
                }
            }
        }
    )
    caso = ImportarCatalogo(
        SQLAlchemyCatalogoRepository(db_session), SQLAlchemyUnitOfWork(db_session)
    )
    assert importar_json(conteudo, caso) == 0
    itens = client.get("/catalogo/destinos").json()["itens"]
    assert len(itens) == 1
    assert itens[0]["categoria"] == "praia"
    assert itens[0]["descricao"] == "Descrição curada"
    assert itens[0]["latitude"] == "-27.500000"
    assert itens[0]["google_place_id"] == "referencia-curada"
    assert client.get("/catalogo/atividades").json()["itens"] == []


@pytest.mark.parametrize("campo,valor", [("latitude", "91"), ("longitude", "181")])
def test_lote_destino_invalido_nao_grava(db_session, campo, valor):
    conteudo = json.dumps(
        {
            "destinos": {
                "cidade": {
                    "nome": "Cidade",
                    "pais_codigo": "BR",
                    campo: valor,
                }
            }
        }
    )
    caso = ImportarCatalogo(
        SQLAlchemyCatalogoRepository(db_session), SQLAlchemyUnitOfWork(db_session)
    )
    with pytest.raises(DadosInvalidos):
        importar_json(conteudo, caso)
    assert db_session.scalar(select(func.count()).select_from(DestinoCatalogoModel)) == 0


def test_check_categoria_no_banco(db_session, destinos):
    destino = db_session.get(DestinoCatalogoModel, destinos[0].id)
    destino.categoria = "invalida"
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_contrato_openapi_destinos_publicos():
    contrato = app.openapi()
    for rota in ("/catalogo/destinos", "/catalogo/destinos/{destino_id}"):
        assert not contrato["paths"][rota]["get"].get("security")
