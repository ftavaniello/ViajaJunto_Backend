import pytest
from fastapi.testclient import TestClient

from app.adapters.outbound.persistence.avaliacao_model import AvaliacaoModel
from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.infrastructure.database import get_db
from app.main import app

URL = "/catalogo/destinos/ranking"


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
    destinos = {
        nome: repo.salvar_destino(DestinoCatalogo(nome=nome, pais_codigo=pais))
        for nome, pais in (("Lisboa", "PT"), ("Rio", "BR"), ("Paris", "FR"), ("Quito", "EC"))
    }
    atividades = {
        nome: repo.salvar_atividade(
            AtividadeCatalogo(destino=destinos[destino], nome=nome, categoria="cultura")
        ).id
        for nome, destino in (
            ("Museu", "Lisboa"), ("Elétrico", "Lisboa"), ("Cristo", "Rio"), ("Louvre", "Paris"),
        )
    }
    db_session.commit()
    return {"destinos": {n: d.id for n, d in destinos.items()}, "atividades": atividades}


def avaliar(db_session, atividade_id, *notas):
    for nota in notas:
        db_session.add(AvaliacaoModel(catalogo_atividade_id=atividade_id, nota=nota))
    db_session.commit()


def ranking(client, catalogo, **params):
    response = client.get(URL, params=params)
    assert response.status_code == 200, response.text
    corpo = response.json()
    nossos = set(catalogo["destinos"].values())
    return corpo, [i["destino"]["nome"] for i in corpo["itens"] if i["destino"]["id"] in nossos]


def test_ranking_publico_ordenado_com_notas_agregadas_das_atividades(client, catalogo, db_session):
    a = catalogo["atividades"]
    avaliar(db_session, a["Museu"], 5, 5, 4)
    avaliar(db_session, a["Elétrico"], 5, 4)
    avaliar(db_session, a["Cristo"], 5)  # uma única nota máxima
    avaliar(db_session, a["Louvre"], 2, 3)

    corpo, nomes = ranking(client, catalogo, limite=50)

    assert nomes == ["Lisboa", "Rio", "Paris"]
    lisboa = next(i for i in corpo["itens"] if i["destino"]["nome"] == "Lisboa")
    assert lisboa["total_avaliacoes"] == 5
    assert lisboa["media_avaliacoes"] == 4.6
    assert 1 <= lisboa["nota_ranking"] <= 5
    assert lisboa["destino"]["pais_codigo"] == "PT"
    assert corpo["peso_priori"] == 5
    assert [i["posicao"] for i in corpo["itens"]] == list(range(1, len(corpo["itens"]) + 1))


def test_destino_sem_avaliacao_nao_aparece(client, catalogo, db_session):
    avaliar(db_session, catalogo["atividades"]["Cristo"], 4)

    _, nomes = ranking(client, catalogo, limite=50)

    assert "Quito" not in nomes and "Paris" not in nomes


def test_nova_avaliacao_atualiza_o_ranking(client, catalogo, db_session):
    a = catalogo["atividades"]
    avaliar(db_session, a["Cristo"], 4)
    avaliar(db_session, a["Louvre"], 3)
    assert ranking(client, catalogo, limite=50)[1] == ["Rio", "Paris"]

    avaliar(db_session, a["Louvre"], 5, 5, 5, 5)

    assert ranking(client, catalogo, limite=50)[1] == ["Paris", "Rio"]


def test_limite_e_padrao_de_dez(client, catalogo, db_session):
    for nome in ("Museu", "Cristo", "Louvre"):
        avaliar(db_session, catalogo["atividades"][nome], 4)

    assert len(client.get(URL, params={"limite": 2}).json()["itens"]) == 2
    assert len(client.get(URL).json()["itens"]) <= 10


@pytest.mark.parametrize("limite", ["0", "51", "abc", "-1"])
def test_limite_invalido_retorna_422(client, limite):
    assert client.get(URL, params={"limite": limite}).status_code == 422


def test_rota_de_ranking_nao_conflita_com_detalhe_do_destino(client, catalogo):
    destino_id = catalogo["destinos"]["Lisboa"]

    assert client.get(f"/catalogo/destinos/{destino_id}").json()["nome"] == "Lisboa"
    assert client.get(URL).status_code == 200
