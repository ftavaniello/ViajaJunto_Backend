from fastapi.testclient import TestClient

from app.infrastructure.database import get_db
from app.main import app


def _client_com_sessao_de_teste(db_session) -> TestClient:
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def _cadastrar_e_logar(client: TestClient, email: str, senha: str = "senha123") -> str:
    client.post("/usuarios", json={"nome": "Livia", "email": email, "senha": senha})
    login = client.post("/auth/login", json={"email": email, "senha": senha})
    return login.json()["access_token"]


def test_atualizar_me_altera_nome_e_email(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)
    token = _cadastrar_e_logar(client, email_teste)
    novo_email = email_teste.replace("@", "-novo@")

    response = client.patch(
        "/usuarios/me",
        json={"nome": "Livia Bampi", "email": novo_email},
        headers={"Authorization": f"Bearer {token}"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["nome"] == "Livia Bampi"
    assert body["email"] == novo_email


def test_atualizar_me_rejeita_email_ja_utilizado(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)
    token = _cadastrar_e_logar(client, email_teste)
    outro_email = email_teste.replace("@", "-outro@")
    client.post(
        "/usuarios", json={"nome": "Outro", "email": outro_email, "senha": "senha123"}
    )

    response = client.patch(
        "/usuarios/me",
        json={"email": outro_email},
        headers={"Authorization": f"Bearer {token}"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 400


def test_alterar_senha_permite_login_com_a_nova_senha(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)
    token = _cadastrar_e_logar(client, email_teste)

    response = client.patch(
        "/usuarios/me/senha",
        json={"senha_atual": "senha123", "senha_nova": "senhaNova456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    login_com_senha_antiga = client.post(
        "/auth/login", json={"email": email_teste, "senha": "senha123"}
    )
    login_com_senha_nova = client.post(
        "/auth/login", json={"email": email_teste, "senha": "senhaNova456"}
    )
    app.dependency_overrides.clear()

    assert login_com_senha_antiga.status_code == 401
    assert login_com_senha_nova.status_code == 200


def test_alterar_senha_rejeita_senha_atual_incorreta(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)
    token = _cadastrar_e_logar(client, email_teste)

    response = client.patch(
        "/usuarios/me/senha",
        json={"senha_atual": "errada", "senha_nova": "senhaNova456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 400


def test_excluir_me_remove_usuario_e_invalida_acesso_futuro(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)
    token = _cadastrar_e_logar(client, email_teste)

    response = client.delete(
        "/usuarios/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    me_response = client.get(
        "/usuarios/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    app.dependency_overrides.clear()

    assert me_response.status_code == 401
