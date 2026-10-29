import pytest
from fastapi.testclient import TestClient

from app.adapters.outbound.persistence.viagem_model import MembroViagemModel
from app.domain.enums import PapelMembro
from app.infrastructure.database import get_db
from app.main import app

VIAGEM = {
    "nome": "Europa",
    "descricao": "Férias de julho",
    "data_inicio": "2027-07-01",
    "data_fim": "2027-07-20",
}


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _auth(client: TestClient, email: str) -> tuple[dict, int]:
    """Cadastra e autentica um usuario; retorna o header e o id."""
    client.post("/usuarios", json={"nome": "Livia", "email": email, "senha": "senha123"})
    token = client.post("/auth/login", json={"email": email, "senha": "senha123"})
    headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
    return headers, client.get("/usuarios/me", headers=headers).json()["id"]


def _criar(client: TestClient, headers: dict, **extra) -> dict:
    response = client.post("/viagens", json={**VIAGEM, **extra}, headers=headers)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def participantes(client, db_session, email_teste):
    """Viagem do criador com um editor, um visualizador e um usuario sem acesso."""
    criador, _ = _auth(client, email_teste)
    viagem = _criar(client, criador)
    headers = {"criador": criador}
    for papel in ("editor", "visualizador", "estranho"):
        headers[papel], usuario_id = _auth(client, email_teste.replace("@", f"-{papel}@"))
        if papel != "estranho":
            db_session.add(MembroViagemModel(
                viagem_id=viagem["id"], usuario_id=usuario_id, papel=PapelMembro(papel).value,
            ))
    db_session.flush()
    return viagem, headers


def test_criar_viagem_usa_o_usuario_do_token(client, email_teste):
    headers, usuario_id = _auth(client, email_teste)
    outro_headers, outro_id = _auth(client, email_teste.replace("@", "-outro@"))

    body = _criar(client, headers, criador_id=outro_id, status="concluida")

    assert body["criador_id"] == usuario_id
    assert body["status"] == "planejando"
    assert body["nome"] == "Europa"
    assert body["descricao"] == "Férias de julho"
    assert body["data_inicio"] == "2027-07-01"
    assert "codigo_convite" not in body


def test_criar_viagem_rejeita_fim_antes_do_inicio(client, email_teste):
    headers, _ = _auth(client, email_teste)

    response = client.post(
        "/viagens", json={**VIAGEM, "data_fim": "2027-06-01"}, headers=headers
    )

    assert response.status_code == 400


def test_criar_viagem_exige_campos_obrigatorios(client, email_teste):
    headers, _ = _auth(client, email_teste)

    response = client.post("/viagens", json={"nome": "Europa"}, headers=headers)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("metodo", "rota"),
    [("post", "/viagens"), ("get", "/viagens"), ("get", "/viagens/1"),
     ("patch", "/viagens/1"), ("delete", "/viagens/1")],
)
def test_rotas_de_viagem_exigem_token(client, metodo, rota):
    kwargs = {"json": VIAGEM} if metodo in ("post", "patch") else {}

    assert getattr(client, metodo)(rota, **kwargs).status_code == 401


@pytest.mark.parametrize("papel", ["criador", "editor", "visualizador"])
def test_participantes_consultam_a_viagem(client, participantes, papel):
    viagem, headers = participantes

    response = client.get(f"/viagens/{viagem['id']}", headers=headers[papel])

    assert response.status_code == 200
    assert response.json()["id"] == viagem["id"]


def test_outro_usuario_nao_ve_a_viagem(client, participantes):
    viagem, headers = participantes

    response = client.get(f"/viagens/{viagem['id']}", headers=headers["estranho"])
    inexistente = client.get("/viagens/999999999", headers=headers["estranho"])

    # Mesmo status de uma viagem inexistente: nao revela que o id existe.
    assert response.status_code == inexistente.status_code == 404
    assert response.json() == inexistente.json()


def test_listar_traz_viagens_do_usuario(client, participantes):
    viagem, headers = participantes

    do_editor = client.get("/viagens", headers=headers["editor"]).json()
    do_estranho = client.get("/viagens", headers=headers["estranho"]).json()

    assert [v["id"] for v in do_editor] == [viagem["id"]]
    assert do_estranho == []


@pytest.mark.parametrize("papel", ["criador", "editor"])
def test_criador_e_editor_editam_dados_e_status(client, participantes, papel):
    viagem, headers = participantes

    response = client.patch(
        f"/viagens/{viagem['id']}",
        json={"nome": "Europa 2027", "status": "confirmada"},
        headers=headers[papel],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["nome"] == "Europa 2027"
    assert body["status"] == "confirmada"
    assert body["descricao"] == "Férias de julho"


@pytest.mark.parametrize(("papel", "status"), [("visualizador", 403), ("estranho", 404)])
def test_sem_permissao_nao_edita(client, participantes, papel, status):
    viagem, headers = participantes

    response = client.patch(
        f"/viagens/{viagem['id']}", json={"nome": "Invadida"}, headers=headers[papel]
    )
    atual = client.get(f"/viagens/{viagem['id']}", headers=headers["criador"]).json()

    assert response.status_code == status
    assert atual["nome"] == "Europa"


def test_editar_rejeita_periodo_invalido(client, participantes):
    viagem, headers = participantes

    response = client.patch(
        f"/viagens/{viagem['id']}", json={"data_inicio": "2027-08-01"},
        headers=headers["criador"],
    )

    assert response.status_code == 400


def test_editar_rejeita_status_desconhecido(client, participantes):
    viagem, headers = participantes

    response = client.patch(
        f"/viagens/{viagem['id']}", json={"status": "cancelada"}, headers=headers["criador"]
    )

    assert response.status_code == 422


def test_editar_com_descricao_vazia_remove_a_descricao(client, participantes):
    viagem, headers = participantes

    response = client.patch(
        f"/viagens/{viagem['id']}", json={"descricao": ""}, headers=headers["criador"]
    )

    assert response.json()["descricao"] is None


@pytest.mark.parametrize(("papel", "status"), [
    ("editor", 403), ("visualizador", 403), ("estranho", 404),
])
def test_somente_criador_exclui(client, participantes, papel, status):
    viagem, headers = participantes

    response = client.delete(f"/viagens/{viagem['id']}", headers=headers[papel])

    assert response.status_code == status
    assert client.get(f"/viagens/{viagem['id']}", headers=headers["criador"]).status_code == 200


def test_criador_exclui_e_ninguem_mais_acessa(client, participantes):
    viagem, headers = participantes

    response = client.delete(f"/viagens/{viagem['id']}", headers=headers["criador"])

    assert response.status_code == 204
    for papel in ("criador", "editor", "visualizador"):
        assert client.get(f"/viagens/{viagem['id']}", headers=headers[papel]).status_code == 404
        assert client.get("/viagens", headers=headers[papel]).json() == []
