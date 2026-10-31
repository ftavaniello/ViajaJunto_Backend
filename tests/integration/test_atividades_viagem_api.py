from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.adapters.outbound.persistence.avaliacao_model import AvaliacaoModel
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
from app.adapters.outbound.persistence.viagem_model import MembroViagemModel
from app.adapters.outbound.persistence.viagem_repository_sqlalchemy import (
    SQLAlchemyViagemRepository,
)
from app.application.use_cases.criar_viagem import CriarViagem
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.entities.usuario import Usuario
from app.infrastructure.database import get_db
from app.infrastructure.dependencies import get_gerenciar_atividades_viagem, get_token_service
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
    porto = catalogo.salvar_destino(DestinoCatalogo(nome="Porto", pais_codigo="PT"))
    museu = catalogo.salvar_atividade(
        AtividadeCatalogo(
            destino=lisboa,
            nome="Museu",
            categoria="cultura",
            descricao="Descrição pública",
            endereco="Rua Azul",
            foto_url="https://example.com/museu.jpg",
        )
    )
    outra_atividade = catalogo.salvar_atividade(
        AtividadeCatalogo(destino=porto, nome="Passeio", categoria="lazer")
    )
    repo_destinos = SQLAlchemyDestinoViagemRepository(db_session)
    paradas = [
        repo_destinos.salvar(
            DestinoViagem(
                viagem_id=viagem,
                destino=lisboa,
                ordem=ordem,
                data_chegada=date(2027, 7, 2),
                data_saida=date(2027, 7, 5),
            )
        ).id
        for viagem, ordem in ((viagens[0], 1), (viagens[0], 2), (viagens[1], 1))
    ]
    db_session.commit()
    return {
        "viagem": viagens[0],
        "outra_viagem": viagens[1],
        "parada": paradas[0],
        "outra_parada": paradas[1],
        "parada_outra_viagem": paradas[2],
        "catalogo": museu.id,
        "outro_catalogo": outra_atividade.id,
        "headers": headers,
        "usuarios": usuarios,
        "base": f"/viagens/{viagens[0]}/destinos/{paradas[0]}/atividades",
    }


def adicionar(client, cenario, papel="criador", **campos):
    response = client.post(
        cenario["base"],
        json={
            "catalogo_atividade_id": cenario["catalogo"],
            "data": "2027-07-03",
            **campos,
        },
        headers=cenario["headers"][papel],
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("papel", ["criador", "editor"])
def test_fluxo_atividade_custo_status_e_exclusao(client, cenario, papel):
    nova = adicionar(
        client, cenario, papel=papel, custo_previsto="0.10", hora_inicio="09:00", duracao_minutos=60
    )
    assert nova["custo_previsto"] == "0.10"
    assert nova["status"] == "pendente"
    assert nova["atividade"]["nome"] == "Museu"
    assert nova["atividade"]["endereco"] == "Rua Azul"
    assert nova["atividade"]["foto_url"] == "https://example.com/museu.jpg"
    publico_antes = client.get(f"/catalogo/atividades/{cenario['catalogo']}").json()
    rota = f"{cenario['base']}/{nova['id']}"
    headers = cenario["headers"][papel]
    response = client.patch(
        rota, json={"status": "confirmada", "custo_previsto": "15.25"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["custo_previsto"] == "15.25"
    assert response.json()["status"] == "confirmada"
    response = client.patch(rota, json={"status": "concluida"}, headers=headers)
    assert response.status_code == 200
    concluida = response.json()
    assert concluida["realizada_em"] is not None
    assert concluida["realizada_por_id"] == cenario["usuarios"][papel]
    editada = client.patch(
        rota, json={"custo_previsto": "20.30"}, headers=cenario["headers"]["criador"]
    ).json()
    assert editada["realizada_em"] == concluida["realizada_em"]
    assert editada["realizada_por_id"] == concluida["realizada_por_id"]
    reaberta = client.patch(rota, json={"status": "pendente"}, headers=headers).json()
    assert reaberta["realizada_em"] is None
    assert reaberta["realizada_por_id"] is None
    assert client.get(f"/catalogo/atividades/{cenario['catalogo']}").json() == publico_antes
    assert client.delete(rota, headers=headers).status_code == 204
    assert client.get(cenario["base"], headers=headers).json() == []
    assert client.get(f"/catalogo/atividades/{cenario['catalogo']}").status_code == 200


@pytest.mark.parametrize("papel", ["criador", "editor", "visualizador"])
def test_participantes_leem_sem_expor_email(client, cenario, papel):
    nova = adicionar(client, cenario)
    headers = cenario["headers"][papel]
    assert client.get(cenario["base"], headers=headers).json() == [nova]
    assert client.get(f"{cenario['base']}/{nova['id']}", headers=headers).json() == nova
    assert "email" not in nova


def test_ordem_cronologica_com_nulos_e_empate(client, cenario):
    sem_hora = adicionar(client, cenario)
    tarde = adicionar(client, cenario, hora_inicio="15:00")
    cedo = adicionar(client, cenario, hora_inicio="09:00")
    empate = adicionar(client, cenario, hora_inicio="09:00")
    anterior = adicionar(client, cenario, data="2027-07-02")
    obtidos = client.get(cenario["base"], headers=cenario["headers"]["visualizador"]).json()
    assert [a["id"] for a in obtidos] == [
        anterior["id"],
        cedo["id"],
        empate["id"],
        tarde["id"],
        sem_hora["id"],
    ]


@pytest.mark.parametrize(
    "metodo,sufixo,body",
    [
        ("get", "", None),
        ("get", "/1", None),
        ("post", "", {"catalogo_atividade_id": 1, "data": "2027-07-03"}),
        ("patch", "/1", {}),
        ("delete", "/1", None),
    ],
)
def test_atividades_exigem_token(client, metodo, sufixo, body):
    kwargs = {"json": body} if body is not None else {}
    response = getattr(client, metodo)(f"/viagens/1/destinos/1/atividades{sufixo}", **kwargs)
    assert response.status_code == 401


@pytest.mark.parametrize("papel,status", [("visualizador", 403), ("estranho", 404)])
@pytest.mark.parametrize("metodo", ["post", "patch", "delete"])
def test_sem_permissao_nao_altera_atividades(client, cenario, papel, status, metodo):
    nova = adicionar(client, cenario)
    rota = cenario["base"] if metodo == "post" else f"{cenario['base']}/{nova['id']}"
    kwargs = (
        {"json": {"catalogo_atividade_id": cenario["catalogo"], "data": "2027-07-03"}}
        if metodo == "post"
        else {"json": {"custo_previsto": "999"}}
        if metodo == "patch"
        else {}
    )
    response = getattr(client, metodo)(rota, headers=cenario["headers"][papel], **kwargs)
    assert response.status_code == status
    assert client.get(cenario["base"], headers=cenario["headers"]["criador"]).json() == [nova]


@pytest.mark.parametrize("metodo", ["get", "patch", "delete"])
@pytest.mark.parametrize("contexto", ["outra_parada", "outra_viagem", "parada_errada_na_viagem"])
def test_ids_cruzados_sao_ocultados(client, cenario, metodo, contexto):
    nova = adicionar(client, cenario)
    viagem, parada = cenario["viagem"], cenario["parada"]
    if contexto == "outra_parada":
        parada = cenario["outra_parada"]
    elif contexto == "outra_viagem":
        viagem, parada = cenario["outra_viagem"], cenario["parada_outra_viagem"]
    else:
        viagem = cenario["outra_viagem"]
    rota = f"/viagens/{viagem}/destinos/{parada}/atividades/{nova['id']}"
    kwargs = {"json": {"status": "confirmada"}} if metodo == "patch" else {}
    assert (
        getattr(client, metodo)(rota, headers=cenario["headers"]["criador"], **kwargs).status_code
        == 404
    )


@pytest.mark.parametrize(
    "campos,status",
    [
        ({"catalogo_atividade_id": 999999999}, 404),
        ({"data": "2027-07-01"}, 400),
        ({"data": "2027-07-06"}, 400),
        ({"custo_previsto": "-1"}, 422),
        ({"custo_previsto": "1.001"}, 422),
        ({"custo_previsto": "10000000000"}, 422),
        ({"custo_previsto": "NaN"}, 422),
        ({"duracao_minutos": 0}, 422),
        ({"duracao_minutos": True}, 422),
        ({"hora_inicio": "09:00:00Z"}, 400),
        ({"status": "cancelada"}, 422),
        ({"status": "realizada"}, 422),
        ({"realizada_por_id": 999}, 422),
        ({"realizada_em": "2026-01-01T00:00:00Z"}, 422),
    ],
)
def test_entrada_invalida_nao_grava(client, cenario, campos, status):
    response = client.post(
        cenario["base"],
        json={
            "catalogo_atividade_id": cenario["catalogo"],
            "data": "2027-07-03",
            **campos,
        },
        headers=cenario["headers"]["criador"],
    )
    assert response.status_code == status
    assert client.get(cenario["base"], headers=cenario["headers"]["criador"]).json() == []


def test_atividade_de_outro_destino_do_catalogo_e_recusada(client, cenario):
    response = client.post(
        cenario["base"],
        json={
            "catalogo_atividade_id": cenario["outro_catalogo"],
            "data": "2027-07-03",
        },
        headers=cenario["headers"]["criador"],
    )
    assert response.status_code == 400


def test_patch_omitido_nulo_limpa_opcionais_e_atualiza_data(client, cenario):
    nova = adicionar(client, cenario, hora_inicio="10:30", duracao_minutos=90)
    rota = f"{cenario['base']}/{nova['id']}"
    headers = cenario["headers"]["criador"]
    assert client.patch(rota, json={}, headers=headers).json() == nova
    response = client.patch(
        rota,
        json={
            "hora_inicio": None,
            "duracao_minutos": None,
            "data": "2027-07-04",
            "custo_previsto": None,
            "status": None,
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["hora_inicio"] is None
    assert response.json()["duracao_minutos"] is None
    assert response.json()["data"] == "2027-07-04"
    assert response.json()["custo_previsto"] == "0.00"
    antes = response.json()
    response = client.patch(rota, json={"data": "2027-07-06"}, headers=headers)
    assert response.status_code == 400
    assert client.get(rota, headers=headers).json() == antes


def test_legado_cancelado_preservado_e_pode_ser_replanejado(client, cenario, db_session):
    nova = adicionar(client, cenario)
    model = db_session.get(AtividadeViagemModel, nova["id"])
    model.status = "cancelada"
    db_session.commit()
    rota = f"{cenario['base']}/{nova['id']}"
    headers = cenario["headers"]["criador"]
    assert client.get(rota, headers=headers).json()["status"] == "cancelada"
    response = client.patch(rota, json={"custo_previsto": "1.25"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelada"
    assert (
        client.patch(rota, json={"status": "confirmada"}, headers=headers).json()["status"]
        == "confirmada"
    )


def test_excluir_atividade_preserva_avaliacao_e_catalogo(client, cenario, db_session):
    nova = adicionar(client, cenario, status="concluida")
    avaliacao = AvaliacaoModel(
        usuario_id=cenario["usuarios"]["criador"],
        catalogo_atividade_id=cenario["catalogo"],
        atividade_viagem_id=nova["id"],
        nota=5,
    )
    db_session.add(avaliacao)
    db_session.commit()
    avaliacao_id = avaliacao.id
    assert (
        client.delete(
            f"{cenario['base']}/{nova['id']}", headers=cenario["headers"]["criador"]
        ).status_code
        == 204
    )
    db_session.expire_all()
    assert db_session.get(AtividadeViagemModel, nova["id"]) is None
    assert db_session.get(AvaliacaoModel, avaliacao_id).atividade_viagem_id is None
    assert client.get(f"/catalogo/atividades/{cenario['catalogo']}").status_code == 200


@pytest.mark.parametrize("acao", ["criar", "atualizar", "remover"])
def test_falha_apos_gravacao_reverte_operacao(client, cenario, db_session, monkeypatch, acao):
    nova = adicionar(client, cenario, custo_previsto="10.10")
    caso = get_gerenciar_atividades_viagem(db_session)
    nome_metodo = "deletar" if acao == "remover" else "salvar"
    original = getattr(caso.repository, nome_metodo)

    def falhar(atividade):
        original(atividade)
        raise RuntimeError("falha após flush")

    monkeypatch.setattr(caso.repository, nome_metodo, falhar)
    app.dependency_overrides[get_gerenciar_atividades_viagem] = lambda: caso
    headers = cenario["headers"]["criador"]
    rota = cenario["base"] if acao == "criar" else f"{cenario['base']}/{nova['id']}"
    metodo = {"criar": client.post, "atualizar": client.patch, "remover": client.delete}[acao]
    corpo = (
        {"json": {"catalogo_atividade_id": cenario["catalogo"], "data": "2027-07-03"}}
        if acao == "criar"
        else {"json": {"custo_previsto": "55.55"}}
        if acao == "atualizar"
        else {}
    )
    with pytest.raises(RuntimeError):
        metodo(rota, headers=headers, **corpo)
    assert client.get(cenario["base"], headers=headers).json() == [nova]


def test_atividade_sem_horario_e_lista_vazia(client, cenario):
    headers = cenario["headers"]["criador"]
    assert client.get(cenario["base"], headers=headers).json() == []
    nova = adicionar(client, cenario)
    assert nova["hora_inicio"] is None
    assert nova["duracao_minutos"] is None
    assert client.get(f"{cenario['base']}/999999999", headers=headers).status_code == 404


def test_contrato_atividades_e_protegido():
    contrato = app.openapi()
    for rota, operacoes in contrato["paths"].items():
        if rota.startswith("/viagens/") and "/atividades" in rota:
            for operacao in operacoes.values():
                assert operacao.get("security")
