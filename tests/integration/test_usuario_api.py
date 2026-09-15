from fastapi.testclient import TestClient

from app.infrastructure.database import get_db
from app.main import app


def _client_com_sessao_de_teste(db_session) -> TestClient:
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def test_criar_usuario_via_api_persiste_no_banco(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)

    response = client.post(
        "/usuarios",
        json={"nome": "Livia", "email": email_teste, "senha_hash": "hash123"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["nome"] == "Livia"
    assert body["email"] == email_teste
    assert "senha_hash" not in body


def test_criar_usuario_via_api_rejeita_email_duplicado(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)

    client.post(
        "/usuarios",
        json={"nome": "Livia", "email": email_teste, "senha_hash": "hash123"},
    )
    response = client.post(
        "/usuarios",
        json={"nome": "Livia 2", "email": email_teste, "senha_hash": "hash456"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 400
