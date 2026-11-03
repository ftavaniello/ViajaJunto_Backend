from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.adapters.outbound.persistence.avaliacao_model import AvaliacaoModel
from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.adapters.outbound.persistence.roteiro_model import AtividadeViagemModel, DestinoViagemModel
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
from app.domain.entities.usuario import Usuario
from app.infrastructure.database import get_db
from app.infrastructure.dependencies import get_avaliar_atividade_viagem, get_token_service
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
    for papel in ("criador", "editor", "visualizador", "externo"):
        usuario = SQLAlchemyUsuarioRepository(db_session).salvar(
            Usuario(
                nome=f"Nome {papel}",
                email=email_teste.replace("@", f"-{papel}@"),
                senha_hash="hash",
            )
        )
        usuarios[papel] = usuario.id
        token = get_token_service().gerar_token(usuario.id, usuario.versao_sessao)
        headers[papel] = {"Authorization": "Bearer " + token}
    criar = CriarViagem(SQLAlchemyViagemRepository(db_session), SQLAlchemyUnitOfWork(db_session))
    viagens = [
        criar.execute(
            usuarios["criador"], nome, "SEGREDO DA VIAGEM", date(2027, 1, 1), date(2027, 1, 10)
        ).id
        for nome in ("Primeira", "Segunda")
    ]
    for papel in ("editor", "visualizador"):
        db_session.add(
            MembroViagemModel(viagem_id=viagens[0], usuario_id=usuarios[papel], papel=papel)
        )
    repo = SQLAlchemyCatalogoRepository(db_session)
    lugar = repo.salvar_destino(DestinoCatalogo(nome="Lisboa", pais_codigo="PT"))
    catalogo = [
        repo.salvar_atividade(
            AtividadeCatalogo(
                destino=lugar,
                nome=nome,
                categoria="cultura",
                foto_url="https://example.com/foto.jpg",
            )
        )
        for nome in ("Museu", "Outra", "Sem reviews")
    ]
    paradas, atividades = [], []
    for viagem_id, ordem in ((viagens[0], 1), (viagens[0], 2), (viagens[1], 1)):
        parada = DestinoViagemModel(
            viagem_id=viagem_id,
            destino_catalogo_id=lugar.id,
            ordem=ordem,
            data_chegada=date(2027, 1, 1),
            data_saida=date(2027, 1, 10),
        )
        db_session.add(parada)
        db_session.flush()
        atividade = AtividadeViagemModel(
            destino_viagem_id=parada.id,
            catalogo_atividade_id=catalogo[0].id,
            data=date(2027, 1, 2),
            status="concluida",
            realizada_em=datetime.now(timezone.utc),
            realizada_por_id=usuarios["criador"],
            custo_previsto=99,
        )
        db_session.add(atividade)
        db_session.flush()
        paradas.append(parada.id)
        atividades.append(atividade.id)
    db_session.commit()
    return dict(
        usuarios=usuarios,
        headers=headers,
        viagens=viagens,
        catalogo=[a.id for a in catalogo],
        paradas=paradas,
        atividades=atividades,
    )


def url(c, indice=0):
    return (
        f"/viagens/{c['viagens'][0 if indice < 2 else 1]}/destinos/{c['paradas'][indice]}"
        f"/atividades/{c['atividades'][indice]}/avaliacao"
    )


def detalhe(client, c):
    return client.get(f"/catalogo/atividades/{c['catalogo'][0]}")


@pytest.mark.parametrize("papel", ["criador", "editor", "visualizador"])
def test_participante_publica_review_sem_dados_privados(client, cenario, papel):
    resposta = client.put(
        url(cenario),
        headers=cenario["headers"][papel],
        json={"nota": 5, "comentario": "  Excelente  "},
    )
    assert resposta.status_code == 200, resposta.text
    review = resposta.json()
    assert set(review) == {"id", "nota", "comentario", "autor_nome", "criado_em"}
    assert review["autor_nome"] == f"Nome {papel}"
    assert review["comentario"] == "Excelente"
    publico = detalhe(client, cenario)
    assert publico.status_code == 200
    body = publico.json()
    assert body["media_avaliacoes"] == 5
    assert body["total_avaliacoes"] == 1
    assert body["reviews"] == [review]
    assert body["foto_url"] == "https://example.com/foto.jpg"
    for privado in (
        "@",
        "SEGREDO",
        "custo_previsto",
        "viagem_id",
        "usuario_id",
        "realizada_por_id",
    ):
        assert privado not in publico.text


def test_visitante_le_mas_nao_publica(client, cenario):
    assert client.put(url(cenario), json={"nota": 5}).status_code == 401
    assert detalhe(client, cenario).status_code == 200
    assert (
        client.get(f"/catalogo/atividades/{cenario['catalogo'][0]}/avaliacoes").json()["itens"]
        == []
    )


def test_nao_participante_nao_publica(client, cenario):
    assert (
        client.put(
            url(cenario), headers=cenario["headers"]["externo"], json={"nota": 5}
        ).status_code
        == 404
    )


@pytest.mark.parametrize("status", ["pendente", "confirmada", "cancelada"])
def test_exige_realizacao(client, db_session, cenario, status):
    atividade = db_session.get(AtividadeViagemModel, cenario["atividades"][0])
    atividade.status, atividade.realizada_em = status, None
    db_session.flush()
    assert (
        client.put(
            url(cenario), headers=cenario["headers"]["criador"], json={"nota": 5}
        ).status_code
        == 403
    )
    assert detalhe(client, cenario).json()["total_avaliacoes"] == 0


@pytest.mark.parametrize(
    "corpo",
    [
        {"nota": 0},
        {"nota": 6},
        {"nota": True},
        {"nota": 4.0},
        {"nota": "4"},
        {},
        {"nota": 5, "comentario": "x" * 2001},
        {"nota": 5, "comentario": 42},
        {"nota": 5, "usuario_id": 123},
        {"nota": 5, "catalogo_atividade_id": 123},
    ],
)
def test_payload_invalido(client, cenario, corpo):
    assert (
        client.put(url(cenario), headers=cenario["headers"]["criador"], json=corpo).status_code
        == 422
    )


def test_misturar_ids_nao_publica(client, cenario):
    c = cenario
    caminhos = [
        f"/viagens/{c['viagens'][0]}/destinos/{c['paradas'][1]}/atividades/{c['atividades'][0]}/avaliacao",
        f"/viagens/{c['viagens'][1]}/destinos/{c['paradas'][0]}/atividades/{c['atividades'][0]}/avaliacao",
        f"/viagens/{c['viagens'][0]}/destinos/{c['paradas'][0]}/atividades/{c['atividades'][2]}/avaliacao",
    ]
    for caminho in caminhos:
        assert (
            client.put(caminho, headers=c["headers"]["criador"], json={"nota": 5}).status_code
            == 404
        )


def test_repetir_atualiza_sem_duplicar_entre_ocorrencias_e_viagens(client, db_session, cenario):
    headers = cenario["headers"]["criador"]
    primeira = client.put(
        url(cenario), headers=headers, json={"nota": 5, "comentario": "Antes"}
    ).json()
    for indice in (0, 1, 2):
        atual = client.put(url(cenario, indice), headers=headers, json={"nota": 3}).json()
        assert atual["id"] == primeira["id"]
        assert atual["criado_em"] == primeira["criado_em"]
        assert atual["comentario"] is None
    assert db_session.scalar(select(func.count()).select_from(AvaliacaoModel)) == 1
    assert detalhe(client, cenario).json()["media_avaliacoes"] == 3


def test_media_filtro_e_paginacao_de_reviews(client, cenario):
    for papel, nota in (("criador", 5), ("editor", 4), ("visualizador", 4)):
        assert (
            client.put(
                url(cenario), headers=cenario["headers"][papel], json={"nota": nota}
            ).status_code
            == 200
        )
    body = detalhe(client, cenario).json()
    assert body["media_avaliacoes"] == pytest.approx(13 / 3)
    assert body["total_avaliacoes"] == 3
    consulta = client.get(
        "/catalogo/atividades",
        params={
            "nota_minima": "4.33",
            "nome": "museu",
            "categoria": "cultura",
            "localizacao": "lisboa",
        },
    ).json()
    assert [a["id"] for a in consulta["itens"]] == [cenario["catalogo"][0]]
    assert consulta["itens"][0]["media_avaliacoes"] == body["media_avaliacoes"]
    assert client.get("/catalogo/atividades?nota_minima=4.34").json()["itens"] == []
    assert client.get("/catalogo/atividades?nota_minima=5").json()["itens"] == []
    base = f"/catalogo/atividades/{cenario['catalogo'][0]}/avaliacoes"
    paginas = [
        client.get(base, params={"pagina": p, "tamanho_pagina": 2}).json() for p in (1, 2, 3)
    ]
    assert [p["tem_proxima"] for p in paginas] == [True, False, False]
    assert [r["id"] for p in paginas for r in p["itens"]] == [r["id"] for r in body["reviews"]]


@pytest.mark.parametrize("nota", ["0", "6", "NaN", "Infinity", "abc"])
def test_nota_minima_invalida(client, nota):
    assert client.get("/catalogo/atividades", params={"nota_minima": nota}).status_code == 422


@pytest.mark.parametrize("parametros", [{"pagina": 0}, {"tamanho_pagina": 101}, {"extra": "x"}])
def test_paginacao_de_reviews_invalida(client, cenario, parametros):
    assert (
        client.get(
            f"/catalogo/atividades/{cenario['catalogo'][0]}/avaliacoes", params=parametros
        ).status_code
        == 422
    )


def test_preserva_review_apos_reabrir_e_excluir_viagem_e_anonimiza_apos_excluir_conta(
    client, cenario
):
    c = cenario
    assert client.put(url(c), headers=c["headers"]["criador"], json={"nota": 4}).status_code == 200
    base = f"/viagens/{c['viagens'][0]}/destinos/{c['paradas'][0]}/atividades/{c['atividades'][0]}"
    assert (
        client.patch(base, headers=c["headers"]["criador"], json={"status": "pendente"}).status_code
        == 200
    )
    assert client.put(url(c), headers=c["headers"]["criador"], json={"nota": 5}).status_code == 403
    assert (
        client.delete(f"/viagens/{c['viagens'][0]}", headers=c["headers"]["criador"]).status_code
        == 204
    )
    assert detalhe(client, c).json()["total_avaliacoes"] == 1
    assert client.delete("/usuarios/me", headers=c["headers"]["criador"]).status_code == 204
    body = detalhe(client, c).json()
    assert body["total_avaliacoes"] == 1
    assert body["media_avaliacoes"] == 4
    assert body["reviews"][0]["autor_nome"] is None


def test_falha_apos_flush_desfaz_review(client, db_session, cenario):
    caso = get_avaliar_atividade_viagem(db_session)
    salvar = caso.avaliacoes.salvar

    def falhar(avaliacao):
        salvar(avaliacao)
        raise RuntimeError("Falha após gravação")

    caso.avaliacoes.salvar = falhar
    app.dependency_overrides[get_avaliar_atividade_viagem] = lambda: caso
    with pytest.raises(RuntimeError):
        client.put(url(cenario), headers=cenario["headers"]["criador"], json={"nota": 5})
    assert detalhe(client, cenario).json()["total_avaliacoes"] == 0


def test_reviews_de_atividade_inexistente(client):
    assert client.get("/catalogo/atividades/99999999/avaliacoes").status_code == 404


def test_openapi_publico_e_privado():
    schema = app.openapi()
    caminho = "/viagens/{viagem_id}/destinos/{destino_id}/atividades/{atividade_id}/avaliacao"
    assert schema["paths"][caminho]["put"]["security"]
    assert not schema["paths"]["/catalogo/atividades/{atividade_id}/avaliacoes"]["get"].get(
        "security"
    )


def test_detalhe_limita_reviews_mas_media_considera_todos(client, db_session, cenario):
    for i in range(25):
        db_session.add(
            AvaliacaoModel(
                catalogo_atividade_id=cenario["catalogo"][0],
                nota=1 if i == 0 else 5,
                comentario=f"Review {i}",
            )
        )
    db_session.flush()
    body = detalhe(client, cenario).json()
    assert len(body["reviews"]) == 20
    assert body["total_avaliacoes"] == 25
    assert body["media_avaliacoes"] == pytest.approx(121 / 25)
    pagina2 = client.get(
        f"/catalogo/atividades/{cenario['catalogo'][0]}/avaliacoes?pagina=2"
    ).json()
    assert len(pagina2["itens"]) == 5
    assert pagina2["tem_proxima"] is False
    assert set(r["id"] for r in body["reviews"]).isdisjoint(r["id"] for r in pagina2["itens"])


def test_filtra_antes_de_paginar_sem_duplicar_atividades(client, db_session, cenario):
    for indice, nota in ((0, 5), (0, 4), (1, 4)):
        db_session.add(AvaliacaoModel(catalogo_atividade_id=cenario["catalogo"][indice], nota=nota))
    db_session.flush()
    paginas = [
        client.get(
            "/catalogo/atividades",
            params={
                "nota_minima": 4,
                "tamanho_pagina": 1,
                "pagina": p,
            },
        ).json()
        for p in (1, 2, 3)
    ]
    assert [a["id"] for p in paginas for a in p["itens"]] == cenario["catalogo"][:2]
    assert [p["tem_proxima"] for p in paginas] == [True, False, False]


def test_sem_consultas_por_item_na_listagem(client, db_session, cenario):
    from sqlalchemy import event

    consultas = []

    def registrar(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            consultas.append(statement)

    conexao = db_session.connection()
    event.listen(conexao, "before_cursor_execute", registrar)
    try:
        assert client.get("/catalogo/atividades").status_code == 200
        assert len(consultas) == 1
        consultas.clear()
        assert detalhe(client, cenario).status_code == 200
        assert len(consultas) == 2
    finally:
        event.remove(conexao, "before_cursor_execute", registrar)
