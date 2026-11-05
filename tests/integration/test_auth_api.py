import logging
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.infrastructure.config import settings
from app.infrastructure.database import get_db
from app.main import app


def _token_assinado(payload: dict) -> str:
    """Token com assinatura valida da aplicacao, mas claims controladas pelo teste."""
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _exp(minutos: int = 5) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutos)


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


@pytest.mark.parametrize(
    "authorization",
    [
        lambda: f"Bearer {_token_assinado({'exp': _exp()})}",
        lambda: f"Bearer {_token_assinado({'sub': '1'})}",
        lambda: f"Bearer {_token_assinado({'sub': 'abc', 'exp': _exp()})}",
        lambda: f"Bearer {_token_assinado({'sub': '1', 'exp': _exp(-1)})}",
        lambda: f"Bearer {_token_assinado({'sub': '99999999999999999999', 'exp': _exp()})}",
        lambda: "Basic dXN1YXJpbzpzZW5oYQ==",
        lambda: "Bearer",
    ],
    ids=[
        "sem-sub", "sem-exp", "sub-invalido", "expirado", "usuario-inexistente",
        "esquema-basic", "bearer-sem-token",
    ],
)
def test_autenticacao_invalida_responde_401_sem_erro_interno(db_session, authorization):
    client = _client_com_sessao_de_teste(db_session)

    response = client.get("/usuarios/me", headers={"Authorization": authorization()})
    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json() == {"detail": "Token inválido ou expirado"}


def test_fluxo_de_autenticacao_nao_expoe_credenciais_em_logs(db_session, email_teste, caplog):
    senha = "senha-secreta-do-teste-123"
    client = _client_com_sessao_de_teste(db_session)
    caplog.set_level(logging.DEBUG)

    client.post("/usuarios", json={"nome": "Livia", "email": email_teste, "senha": senha})
    token = client.post(
        "/auth/login", json={"email": email_teste, "senha": senha}
    ).json()["access_token"]
    client.post("/auth/login", json={"email": email_teste, "senha": "senha-errada-123"})
    client.get("/usuarios/me", headers={"Authorization": f"Bearer {token}"})
    client.get("/usuarios/me", headers={"Authorization": f"Bearer {token}x"})
    client.patch(
        "/usuarios/me/senha",
        json={"senha_atual": senha, "senha_nova": "nova-senha-secreta-456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    app.dependency_overrides.clear()

    for credencial in (senha, "senha-errada-123", "nova-senha-secreta-456", token,
                       settings.JWT_SECRET_KEY):
        assert credencial not in caplog.text
