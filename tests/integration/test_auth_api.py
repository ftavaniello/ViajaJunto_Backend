from fastapi.testclient import TestClient

from app.infrastructure.database import get_db
from app.main import app


def _client_com_sessao_de_teste(db_session) -> TestClient:
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def test_login_com_sucesso_retorna_token_e_acessa_endpoint_protegido(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)

    client.post(
        "/usuarios",
        json={"nome": "Livia", "email": email_teste, "senha": "senha123"},
    )

    login_response = client.post(
        "/auth/login",
        json={"email": email_teste, "senha": "senha123"},
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    assert login_response.json()["token_type"] == "bearer"

    me_response = client.get(
        "/usuarios/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    app.dependency_overrides.clear()

    assert me_response.status_code == 200
    assert me_response.json()["email"] == email_teste


def test_login_rejeita_senha_incorreta(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)

    client.post(
        "/usuarios",
        json={"nome": "Livia", "email": email_teste, "senha": "senha123"},
    )
    response = client.post(
        "/auth/login",
        json={"email": email_teste, "senha": "errada"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 401


def test_usuarios_me_rejeita_requisicao_sem_token(db_session):
    client = _client_com_sessao_de_teste(db_session)

    response = client.get("/usuarios/me")
    app.dependency_overrides.clear()

    assert response.status_code == 401


def test_usuarios_me_rejeita_token_invalido(db_session):
    client = _client_com_sessao_de_teste(db_session)

    response = client.get(
        "/usuarios/me",
        headers={"Authorization": "Bearer token-invalido"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 401
