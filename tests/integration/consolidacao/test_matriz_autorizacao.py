from dataclasses import dataclass

import pytest
from sqlalchemy import select

from app.adapters.outbound.persistence.avaliacao_model import AvaliacaoModel
from app.adapters.outbound.persistence.convite_viagem_model import ConviteViagemModel
from app.adapters.outbound.persistence.notificacao_model import NotificacaoModel
from app.adapters.outbound.persistence.roteiro_model import AtividadeViagemModel, DestinoViagemModel
from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.adapters.outbound.persistence.viagem_model import (
    MembroViagemModel,
    OrcamentoModel,
    ViagemModel,
)
from app.main import app
from tests.integration.consolidacao.conftest import SENHA


@dataclass(frozen=True)
class Operacao:
    metodo: str
    caminho: str
    regra: str
    sucesso: int = 200
    corpo: dict | None = None


V = "/viagens/{viagem_id}"
D = V + "/destinos"
P = D + "/{destino_id}"
A = P + "/atividades"
ATIVIDADE = A + "/{atividade_id}"
OPERACOES = [
    Operacao("POST", "/auth/logout", "conta", 204),
    Operacao("GET", "/usuarios/me", "conta"),
    Operacao("GET", "/usuarios/resumo", "conta"),
    Operacao("PATCH", "/usuarios/me", "conta", corpo={"nome": "Atualizado"}),
    Operacao(
        "PATCH",
        "/usuarios/me/senha",
        "conta",
        204,
        {"senha_atual": SENHA, "senha_nova": "OutraSenha123!"},
    ),
    Operacao("DELETE", "/usuarios/me", "excluir_conta", 204),
    Operacao("GET", "/usuarios/me/paises-visitados", "conta"),
    Operacao("GET", "/viagens", "conta"),
    Operacao(
        "POST",
        "/viagens",
        "conta",
        201,
        {
            "nome": "Nova viagem",
            "data_inicio": "2027-01-01",
            "data_fim": "2027-01-10",
        },
    ),
    Operacao("GET", V, "leitura"),
    Operacao("PATCH", V, "edicao", corpo={"nome": "Alterada"}),
    Operacao("DELETE", V, "criador", 204),
    Operacao("GET", V + "/mapa", "leitura"),
    Operacao("GET", V + "/membros", "leitura"),
    Operacao("PATCH", V + "/membros/{membro_id}", "criador", corpo={"papel": "visualizador"}),
    Operacao("DELETE", V + "/membros/{membro_id}", "criador", 204),
    Operacao("GET", V + "/convites", "criador"),
    Operacao("POST", V + "/convites", "criador", 201, {"email": "novo@example.com"}),
    Operacao("DELETE", V + "/convites/{convite_id}", "criador", 204),
    Operacao("POST", "/viagens/convites/aceitar", "aceite", 201, {"token": "segredo-0"}),
    Operacao("GET", D, "leitura"),
    Operacao(
        "POST",
        D,
        "edicao",
        201,
        {
            "destino_catalogo_id": "{catalogo_destino}",
            "data_chegada": "2027-01-01",
            "data_saida": "2027-01-10",
        },
    ),
    Operacao("PUT", D + "/ordem", "edicao", corpo={"destinos_ids": ["{destino_id}"]}),
    Operacao("GET", P, "leitura"),
    Operacao("PATCH", P, "edicao", corpo={"descricao": "Alteração particular"}),
    Operacao("DELETE", P, "edicao", 204),
    Operacao("GET", A, "leitura"),
    Operacao(
        "POST",
        A,
        "edicao",
        201,
        {
            "catalogo_atividade_id": "{catalogo_atividade}",
            "data": "2027-01-02",
        },
    ),
    Operacao("GET", ATIVIDADE, "leitura"),
    Operacao("PATCH", ATIVIDADE, "edicao", corpo={"custo_previsto": "150.25"}),
    Operacao("DELETE", ATIVIDADE, "edicao", 204),
    Operacao("PUT", ATIVIDADE + "/avaliacao", "leitura", corpo={"nota": 5}),
    Operacao("GET", V + "/orcamento", "leitura"),
    Operacao("PUT", V + "/orcamento", "edicao", corpo={"valor_total": "1000.00"}),
    Operacao("GET", "/notificacoes", "conta"),
    Operacao("GET", "/notificacoes/nao-lidas/contagem", "conta"),
    Operacao("PATCH", "/notificacoes/{notificacao_id}/lida", "conta"),
    Operacao("POST", "/notificacoes/marcar-todas-lidas", "conta"),
]
PAPEIS = ["criador", "editor", "visualizador", "externo", "removido", "anonimo", "invalido"]


def preencher(valor, contexto):
    if isinstance(valor, dict):
        return {k: preencher(v, contexto) for k, v in valor.items()}
    if isinstance(valor, list):
        return [preencher(v, contexto) for v in valor]
    if isinstance(valor, str) and valor.startswith("{") and valor.endswith("}"):
        return contexto[valor[1:-1]]
    return valor


def estado(db):
    # Compara valores, não somente contagens: negações não podem editar registros.
    tabelas = [
        UsuarioModel,
        ViagemModel,
        MembroViagemModel,
        OrcamentoModel,
        DestinoViagemModel,
        AtividadeViagemModel,
        AvaliacaoModel,
        ConviteViagemModel,
        NotificacaoModel,
    ]
    return [
        list(db.execute(select(m.__table__).order_by(*m.__table__.primary_key))) for m in tabelas
    ]


def esperado(op, papel):
    if papel in ("anonimo", "invalido"):
        return 401
    if op.regra == "aceite":
        return 201 if papel == "externo" else 403
    if op.regra == "excluir_conta":
        return 409 if papel == "criador" else 204
    if op.regra == "conta":
        return op.sucesso
    if papel in ("externo", "removido"):
        return 404
    if op.regra == "criador" and papel != "criador":
        return 403
    if op.regra == "edicao" and papel == "visualizador":
        return 403
    return op.sucesso


@pytest.mark.parametrize("papel", PAPEIS)
@pytest.mark.parametrize("op", OPERACOES, ids=lambda op: f"{op.metodo} {op.caminho}")
def test_matriz_de_todos_os_recursos_privados(api_integrada, matriz, db_session, op, papel):
    client, _ = api_integrada
    contexto = {
        **matriz,
        "catalogo_destino": matriz["catalogo"][0],
        "catalogo_atividade": matriz["catalogo"][1],
        "notificacao_id": matriz["notificacoes"].get(papel, matriz["notificacoes"]["criador"]),
    }
    antes = estado(db_session)
    r = client.request(
        op.metodo,
        op.caminho.format_map(contexto),
        headers=matriz["headers"][papel],
        json=preencher(op.corpo, contexto),
    )
    codigo = esperado(op, papel)
    assert r.status_code == codigo, r.text
    if codigo >= 400:
        assert estado(db_session) == antes


def test_inventario_exige_cobertura_de_novas_operacoes_privadas():
    privadas = {
        (m.upper(), p)
        for p, metodos in app.openapi()["paths"].items()
        for m, dados in metodos.items()
        if dados.get("security")
    }
    cobertas = {(o.metodo, o.caminho) for o in OPERACOES}
    assert privadas == cobertas, "Atualize a matriz ao adicionar ou remover operações privadas"


FILHOS = [
    ("GET", D + "/{outro_destino}", None),
    ("PATCH", D + "/{outro_destino}", {"descricao": "Não pode mudar"}),
    ("DELETE", D + "/{outro_destino}", None),
    ("GET", D + "/{outro_destino}/atividades", None),
    (
        "POST",
        D + "/{outro_destino}/atividades",
        {"catalogo_atividade_id": "{catalogo_atividade}", "data": "2027-01-02"},
    ),
    ("GET", A + "/{outra_atividade}", None),
    ("PATCH", A + "/{outra_atividade}", {"custo_previsto": "1.00"}),
    ("DELETE", A + "/{outra_atividade}", None),
    ("PUT", A + "/{outra_atividade}/avaliacao", {"nota": 5}),
    ("DELETE", V + "/convites/{outro_convite}", None),
    ("PATCH", V + "/membros/{outro_membro}", {"papel": "visualizador"}),
    ("DELETE", V + "/membros/{outro_membro}", None),
]


@pytest.mark.parametrize("papel", ["criador", "editor"])
@pytest.mark.parametrize("metodo,caminho,corpo", FILHOS)
def test_ids_filhos_de_outra_viagem_nao_atravessam_contexto(
    api_integrada,
    matriz,
    db_session,
    papel,
    metodo,
    caminho,
    corpo,
):
    client, _ = api_integrada
    contexto = {
        **matriz,
        "outro_membro": matriz["usuarios"]["externo"],
        "catalogo_atividade": matriz["catalogo"][1],
    }
    antes = estado(db_session)
    r = client.request(
        metodo,
        caminho.format_map(contexto),
        headers=matriz["headers"][papel],
        json=preencher(corpo, contexto),
    )
    # Gestão de membros/convites é negada ao editor antes da procura do filho.
    codigo = (
        403 if papel == "editor" and ("/membros/" in caminho or "/convites/" in caminho) else 404
    )
    assert r.status_code == codigo, r.text
    assert estado(db_session) == antes


@pytest.mark.parametrize("papel", ["criador", "editor", "visualizador", "externo", "removido"])
def test_notificacao_de_outro_usuario_e_isolada(api_integrada, matriz, db_session, papel):
    outro = "editor" if papel == "criador" else "criador"
    antes = estado(db_session)
    r = api_integrada[0].patch(
        f"/notificacoes/{matriz['notificacoes'][outro]}/lida", headers=matriz["headers"][papel]
    )
    assert r.status_code == 404
    assert estado(db_session) == antes


def test_listas_pessoais_nao_vazam_viagens_ou_notificacoes(api_integrada, matriz):
    client, _ = api_integrada
    for papel in ("editor", "visualizador", "externo", "removido"):
        headers = matriz["headers"][papel]
        viagens = client.get("/viagens", headers=headers).json()["itens"]
        ids = {v["id"] for v in viagens}
        alvo = (
            {matriz["outra_viagem"]}
            if papel == "externo"
            else (set() if papel == "removido" else {matriz["viagem_id"]})
        )
        assert ids == alvo
        notificacoes = client.get("/notificacoes", headers=headers).json()["itens"]
        assert {n["id"] for n in notificacoes} == {matriz["notificacoes"][papel]}
