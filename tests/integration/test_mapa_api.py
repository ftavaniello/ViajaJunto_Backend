from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.adapters.outbound.persistence.destino_viagem_repository_sqlalchemy import (
    SQLAlchemyDestinoViagemRepository,
)
from app.adapters.outbound.persistence.unit_of_work_sqlalchemy import SQLAlchemyUnitOfWork
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.persistence.viagem_model import MembroViagemModel, ViagemModel
from app.adapters.outbound.persistence.viagem_repository_sqlalchemy import (
    SQLAlchemyViagemRepository,
)
from app.application.use_cases.criar_viagem import CriarViagem
from app.domain.entities.catalogo import DestinoCatalogo
from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.entities.usuario import Usuario
from app.infrastructure.database import get_db
from app.infrastructure.dependencies import get_token_service
from app.main import app

# Datas longe de "hoje" para o critério de visita não depender do dia da execução.
PASSADO = date(2020, 3, 1)
FUTURO = date(2099, 3, 1)


@pytest.fixture
def client(db_session):
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def cenario(db_session, email_teste):
    usuarios, headers = {}, {}
    for nome in ("ana", "bruno", "carla"):
        usuario = SQLAlchemyUsuarioRepository(db_session).salvar(
            Usuario(nome=nome, email=email_teste.replace("@", f"-{nome}@"), senha_hash="hash")
        )
        usuarios[nome] = usuario.id
        token = get_token_service().gerar_token(usuario.id, usuario.versao_sessao)
        headers[nome] = {"Authorization": f"Bearer {token}"}

    catalogo = SQLAlchemyCatalogoRepository(db_session)
    lisboa = catalogo.salvar_destino(
        DestinoCatalogo(
            nome="Lisboa", pais_codigo="PT",
            latitude=Decimal("38.722300"), longitude=Decimal("-9.139300"),
        )
    )
    porto = catalogo.salvar_destino(
        DestinoCatalogo(
            nome="Porto", pais_codigo="PT",
            latitude=Decimal("41.157900"), longitude=Decimal("-8.629100"),
        )
    )
    rio = catalogo.salvar_destino(DestinoCatalogo(nome="Rio", pais_codigo="BR"))
    tokyo = catalogo.salvar_destino(DestinoCatalogo(nome="Tóquio", pais_codigo="JP"))
    paris = catalogo.salvar_destino(DestinoCatalogo(nome="Paris", pais_codigo="FR"))

    criar = CriarViagem(SQLAlchemyViagemRepository(db_session), SQLAlchemyUnitOfWork(db_session))
    repo_destinos = SQLAlchemyDestinoViagemRepository(db_session)

    def viagem(dono, status, inicio, paradas):
        v = criar.execute(usuarios[dono], "Viagem", None, inicio, inicio.replace(day=28))
        db_session.get(ViagemModel, v.id).status = status
        for ordem, (destino, dia) in enumerate(paradas, start=1):
            chegada = inicio.replace(day=dia)
            repo_destinos.salvar(
                DestinoViagem(
                    viagem_id=v.id, destino=destino, ordem=ordem,
                    data_chegada=chegada, data_saida=chegada,
                )
            )
        return v.id

    ids = {
        # Porto antes de Lisboa na ordem de visita, mesmo chegando depois.
        "passada": viagem("ana", "concluida", PASSADO, [(porto, 5), (lisboa, 2), (porto, 9)]),
        "futura": viagem("ana", "confirmada", FUTURO, [(tokyo, 2)]),
        "plano": viagem("ana", "planejando", PASSADO, [(paris, 3)]),
        "compartilhada": viagem("bruno", "confirmada", PASSADO, [(rio, 4), (lisboa, 10)]),
        "da_carla": viagem("carla", "concluida", PASSADO, [(paris, 3)]),
    }
    db_session.add(
        MembroViagemModel(
            viagem_id=ids["compartilhada"], usuario_id=usuarios["ana"], papel="visualizador"
        )
    )
    db_session.commit()
    return {"ids": ids, "headers": headers, "usuarios": usuarios}


def paises(client, cenario, usuario):
    response = client.get("/usuarios/me/paises-visitados", headers=cenario["headers"][usuario])
    assert response.status_code == 200, response.text
    return response.json()


def test_paises_visitados_sem_repeticao_e_sem_viagens_futuras_ou_em_planejamento(client, cenario):
    corpo = paises(client, cenario, "ana")

    assert corpo["total"] == 2
    assert corpo["paises"] == [
        {
            "pais_codigo": "BR",
            "primeira_visita": "2020-03-04",
            "ultima_visita": "2020-03-04",
            "total_viagens": 1,
        },
        {
            "pais_codigo": "PT",
            "primeira_visita": "2020-03-02",
            "ultima_visita": "2020-03-10",
            "total_viagens": 2,
        },
    ]


def test_cada_usuario_ve_apenas_os_proprios_paises(client, cenario):
    assert [p["pais_codigo"] for p in paises(client, cenario, "bruno")["paises"]] == ["BR", "PT"]
    assert [p["pais_codigo"] for p in paises(client, cenario, "carla")["paises"]] == ["FR"]


def test_paises_visitados_exige_autenticacao(client):
    assert client.get("/usuarios/me/paises-visitados").status_code == 401


def test_usuario_sem_viagens_recebe_lista_vazia(client, db_session, email_teste):
    usuario = SQLAlchemyUsuarioRepository(db_session).salvar(
        Usuario(nome="Novo", email=email_teste, senha_hash="hash")
    )
    db_session.commit()
    token = get_token_service().gerar_token(usuario.id, usuario.versao_sessao)

    response = client.get(
        "/usuarios/me/paises-visitados", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.json() == {"total": 0, "paises": []}


def test_mapa_da_viagem_traz_paradas_na_ordem_com_coordenadas(client, cenario):
    viagem_id = cenario["ids"]["passada"]

    response = client.get(f"/viagens/{viagem_id}/mapa", headers=cenario["headers"]["ana"])

    assert response.status_code == 200, response.text
    corpo = response.json()
    assert corpo["viagem_id"] == viagem_id
    assert [(p["ordem"], p["nome"]) for p in corpo["paradas"]] == [
        (1, "Porto"), (2, "Lisboa"), (3, "Porto"),
    ]
    porto = corpo["paradas"][0]
    assert porto["pais_codigo"] == "PT"
    assert (porto["latitude"], porto["longitude"]) == (41.1579, -8.6291)
    assert porto["data_chegada"] == "2020-03-05"
    assert {"parada_id", "destino_catalogo_id", "data_saida"} <= porto.keys()


def test_mapa_aceita_destino_sem_coordenadas_e_viagem_compartilhada(client, cenario):
    viagem_id = cenario["ids"]["compartilhada"]

    response = client.get(f"/viagens/{viagem_id}/mapa", headers=cenario["headers"]["ana"])

    assert response.status_code == 200, response.text
    rio = response.json()["paradas"][0]
    assert (rio["nome"], rio["latitude"], rio["longitude"]) == ("Rio", None, None)


def test_mapa_restrito_a_participantes(client, cenario):
    url = f"/viagens/{cenario['ids']['passada']}/mapa"

    assert client.get(url).status_code == 401
    assert client.get(url, headers=cenario["headers"]["carla"]).status_code == 404
    inexistente = client.get("/viagens/999999999/mapa", headers=cenario["headers"]["ana"])
    assert inexistente.status_code == 404


def test_mapa_de_viagem_sem_paradas(client, cenario, db_session):
    criar = CriarViagem(SQLAlchemyViagemRepository(db_session), SQLAlchemyUnitOfWork(db_session))
    vazia = criar.execute(cenario["usuarios"]["ana"], "Vazia", None, FUTURO, FUTURO)

    response = client.get(f"/viagens/{vazia.id}/mapa", headers=cenario["headers"]["ana"])

    assert response.json() == {"viagem_id": vazia.id, "paradas": []}
