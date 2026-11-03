from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

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
from app.adapters.outbound.persistence.viagem_model import MembroViagemModel, OrcamentoModel
from app.adapters.outbound.persistence.viagem_repository_sqlalchemy import (
    SQLAlchemyViagemRepository,
)
from app.application.use_cases.criar_viagem import CriarViagem
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.entities.usuario import Usuario
from app.infrastructure.database import get_db
from app.infrastructure.dependencies import get_token_service
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
def cenario(db_session, email_teste):
    usuarios, headers = {}, {}
    for papel in ("criador", "editor", "visualizador", "estranho"):
        usuario = SQLAlchemyUsuarioRepository(db_session).salvar(
            Usuario(
                nome=papel,
                email=email_teste.replace("@", f"-{papel}@"),
                senha_hash="hash-de-teste",
            )
        )
        usuarios[papel] = usuario.id
        token = get_token_service().gerar_token(usuario.id, usuario.versao_sessao)
        headers[papel] = {"Authorization": f"Bearer {token}"}
    criar = CriarViagem(SQLAlchemyViagemRepository(db_session), SQLAlchemyUnitOfWork(db_session))
    viagens = [
        criar.execute(usuarios["criador"], nome, None, date(2027, 7, 1), date(2027, 7, 20)).id
        for nome in ("Europa", "Outra")
    ]
    for papel in ("editor", "visualizador"):
        db_session.add(
            MembroViagemModel(viagem_id=viagens[0], usuario_id=usuarios[papel], papel=papel)
        )
    catalogo = SQLAlchemyCatalogoRepository(db_session)
    lisboa = catalogo.salvar_destino(DestinoCatalogo(nome="Lisboa", pais_codigo="PT"))
    atividades = {
        categoria: catalogo.salvar_atividade(
            AtividadeCatalogo(destino=lisboa, nome=categoria.title(), categoria=categoria)
        ).id
        for categoria in ("cultura", "lazer", "alimentacao")
    }
    repo_destinos = SQLAlchemyDestinoViagemRepository(db_session)
    paradas = [
        repo_destinos.salvar(
            DestinoViagem(
                viagem_id=viagem,
                destino=lisboa,
                ordem=1,
                data_chegada=date(2027, 7, 2),
                data_saida=date(2027, 7, 5),
            )
        ).id
        for viagem in viagens
    ]
    db_session.commit()
    return {
        "viagem": viagens[0],
        "outra_viagem": viagens[1],
        "paradas": paradas,
        "atividades": atividades,
        "headers": headers,
        "url": f"/viagens/{viagens[0]}/orcamento",
    }


def adicionar(client, cenario, categoria, custo, indice=0):
    viagem = (cenario["viagem"], cenario["outra_viagem"])[indice]
    response = client.post(
        f"/viagens/{viagem}/destinos/{cenario['paradas'][indice]}/atividades",
        json={
            "catalogo_atividade_id": cenario["atividades"][categoria],
            "data": "2027-07-03",
            "custo_previsto": custo,
        },
        headers=cenario["headers"]["criador"],
    )
    assert response.status_code == 201, response.text
    return response.json()


def definir(client, cenario, valor, papel="criador"):
    headers = cenario["headers"][papel]
    return client.put(cenario["url"], json={"valor_total": valor}, headers=headers)


def resumo(client, cenario, papel="criador"):
    response = client.get(cenario["url"], headers=cenario["headers"][papel])
    assert response.status_code == 200, response.text
    return response.json()


def categoria(corpo, nome):
    return next(c for c in corpo["categorias"] if c["categoria"] == nome)


def test_resumo_sem_orcamento_e_sem_atividades(client, cenario):
    corpo = resumo(client, cenario)

    assert corpo["orcamento_total"] is None
    assert corpo["total_planejado"] == "0.00"
    assert corpo["saldo_disponivel"] is None
    assert corpo["percentual_consumido"] is None
    assert corpo["orcamento_excedido"] is False
    assert len(corpo["categorias"]) == 6
    assert categoria(corpo, "cultura") == {
        "categoria": "cultura",
        "total_planejado": "0.00",
        "percentual_orcamento": None,
        "percentual_planejado": None,
    }


def test_exemplo_1000_com_300_planejados_e_recalculo(client, cenario):
    adicionar(client, cenario, "cultura", "200.00")
    lazer = adicionar(client, cenario, "lazer", "100.00")
    adicionar(client, cenario, "alimentacao", "5000.00", indice=1)  # outra viagem

    response = definir(client, cenario, "1000")
    assert response.status_code == 200, response.text
    corpo = response.json()
    assert corpo["viagem_id"] == cenario["viagem"]
    assert (corpo["orcamento_total"], corpo["total_planejado"], corpo["saldo_disponivel"]) == (
        "1000.00",
        "300.00",
        "700.00",
    )
    assert corpo["percentual_consumido"] == "30.00"
    assert categoria(corpo, "cultura")["percentual_orcamento"] == "20.00"
    assert categoria(corpo, "cultura")["percentual_planejado"] == "66.67"
    assert categoria(corpo, "lazer")["percentual_planejado"] == "33.33"
    assert categoria(corpo, "alimentacao")["total_planejado"] == "0.00"

    url_lazer = (
        f"/viagens/{cenario['viagem']}/destinos/{cenario['paradas'][0]}/atividades/{lazer['id']}"
    )
    headers = cenario["headers"]["editor"]
    response = client.patch(url_lazer, json={"custo_previsto": "350.50"}, headers=headers)
    assert response.status_code == 200, response.text
    corpo = resumo(client, cenario, "visualizador")
    assert corpo["total_planejado"] == "550.50"
    assert corpo["saldo_disponivel"] == "449.50"

    assert client.delete(url_lazer, headers=headers).status_code == 204
    corpo = resumo(client, cenario)
    assert corpo["total_planejado"] == "200.00"
    assert corpo["saldo_disponivel"] == "800.00"
    assert categoria(corpo, "lazer")["total_planejado"] == "0.00"


def test_orcamento_unico_editavel_e_gravado_como_decimal(client, cenario, db_session):
    assert definir(client, cenario, "1000.00").status_code == 200
    response = definir(client, cenario, "1234.56", papel="editor")
    assert response.status_code == 200, response.text
    assert response.json()["orcamento_total"] == "1234.56"

    linhas = db_session.scalars(
        select(OrcamentoModel).where(OrcamentoModel.viagem_id == cenario["viagem"])
    ).all()
    assert len(linhas) == 1
    assert linhas[0].limite_total == Decimal("1234.56")
    assert isinstance(linhas[0].limite_total, Decimal)
    outra = client.get(
        f"/viagens/{cenario['outra_viagem']}/orcamento", headers=cenario["headers"]["criador"]
    )
    assert outra.json()["orcamento_total"] is None


def test_linha_legada_com_limite_nulo_equivale_a_sem_orcamento(client, cenario, db_session):
    db_session.add(OrcamentoModel(viagem_id=cenario["viagem"], limite_total=None))
    db_session.commit()

    assert resumo(client, cenario)["orcamento_total"] is None
    assert definir(client, cenario, "10").json()["orcamento_total"] == "10.00"
    total = db_session.scalar(
        select(func.count()).select_from(OrcamentoModel).where(
            OrcamentoModel.viagem_id == cenario["viagem"]
        )
    )
    assert total == 1


def test_estouro_e_orcamento_zero(client, cenario):
    adicionar(client, cenario, "cultura", "150.00")

    corpo = definir(client, cenario, "100").json()
    assert corpo["saldo_disponivel"] == "-50.00"
    assert corpo["percentual_consumido"] == "150.00"
    assert corpo["orcamento_excedido"] is True

    corpo = definir(client, cenario, "0").json()
    assert corpo["orcamento_total"] == "0.00"
    assert corpo["saldo_disponivel"] == "-150.00"
    assert corpo["percentual_consumido"] is None
    assert categoria(corpo, "cultura")["percentual_orcamento"] is None
    assert categoria(corpo, "cultura")["percentual_planejado"] == "100.00"


def test_atividades_canceladas_legadas_ficam_fora_do_total(client, cenario, db_session):
    legada = adicionar(client, cenario, "cultura", "80.00")
    adicionar(client, cenario, "lazer", "20.00")
    db_session.get(AtividadeViagemModel, legada["id"]).status = "cancelada"
    db_session.commit()

    assert resumo(client, cenario)["total_planejado"] == "20.00"


def test_permissoes(client, cenario):
    assert definir(client, cenario, "500").status_code == 200

    assert resumo(client, cenario, "visualizador")["orcamento_total"] == "500.00"
    response = definir(client, cenario, "1", papel="visualizador")
    assert response.status_code == 403
    estranho = cenario["headers"]["estranho"]
    for metodo in ("get", "put"):
        response = client.request(
            metodo, cenario["url"], json={"valor_total": "1"}, headers=estranho
        )
        assert response.status_code == 404
        assert client.request(metodo, cenario["url"], json={"valor_total": "1"}).status_code == 401
    inexistente = client.get("/viagens/999999999/orcamento", headers=cenario["headers"]["criador"])
    assert inexistente.status_code == 404
    assert resumo(client, cenario)["orcamento_total"] == "500.00"


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {"valor_total": None},
        {"valor_total": "-0.01"},
        {"valor_total": "1.001"},
        {"valor_total": "10000000000"},
        {"valor_total": "NaN"},
        {"valor_total": "Infinity"},
        {"valor_total": "abc"},
        {"valor_total": "10", "viagem_id": 2},
    ],
)
def test_valor_invalido_retorna_422_sem_gravar(client, cenario, corpo):
    response = client.put(cenario["url"], json=corpo, headers=cenario["headers"]["criador"])

    assert response.status_code == 422
    assert resumo(client, cenario)["orcamento_total"] is None
