"""Contrato de sessao da API (RF02): ver docs/sessoes-e-logout.md."""
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.adapters.outbound.persistence.token_revogado_model import TokenRevogadoModel
from app.adapters.outbound.security.pyjwt_token_service import PyJWTTokenService
from app.infrastructure.config import settings
from app.infrastructure.database import get_db
from app.main import app


def _client_com_sessao_de_teste(db_session) -> TestClient:
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def _login(client: TestClient, email: str, senha: str = "senha123") -> dict:
    response = client.post("/auth/login", json={"email": email, "senha": senha})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _cadastrar(client: TestClient, email: str) -> None:
    response = client.post("/usuarios", json={"nome": "Livia", "email": email, "senha": "senha123"})
    assert response.status_code == 201


def test_logout_encerra_o_token_no_servidor(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)
    _cadastrar(client, email_teste)
    auth = _login(client, email_teste)
    assert client.get("/usuarios/me", headers=auth).status_code == 200

    logout = client.post("/auth/logout", headers=auth)
    me = client.get("/usuarios/me", headers=auth)
    app.dependency_overrides.clear()

    assert logout.status_code == 204
    assert me.status_code == 401
    assert me.headers["WWW-Authenticate"] == "Bearer"


def test_token_copiado_antes_do_logout_e_recusado_em_todas_as_rotas(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)
    _cadastrar(client, email_teste)
    auth = _login(client, email_teste)
    copia = dict(auth)

    client.post("/auth/logout", headers=auth)
    respostas = [
        client.get("/usuarios/me", headers=copia),
        client.patch("/usuarios/me", json={"nome": "Outro"}, headers=copia),
        client.patch(
            "/usuarios/me/senha",
            json={"senha_atual": "senha123", "senha_nova": "senhaNova456"},
            headers=copia,
        ),
        client.delete("/usuarios/me", headers=copia),
        client.post("/auth/logout", headers=copia),
    ]
    app.dependency_overrides.clear()

    assert [r.status_code for r in respostas] == [401] * len(respostas)


def test_logout_nao_afeta_outras_sessoes_e_permite_novo_login(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)
    _cadastrar(client, email_teste)
    sessao_a = _login(client, email_teste)
    sessao_b = _login(client, email_teste)

    client.post("/auth/logout", headers=sessao_a)
    me_b = client.get("/usuarios/me", headers=sessao_b)
    me_novo_login = client.get("/usuarios/me", headers=_login(client, email_teste))
    app.dependency_overrides.clear()

    assert me_b.status_code == 200
    assert me_novo_login.status_code == 200


def test_logout_grava_apenas_o_jti_e_a_expiracao(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)
    _cadastrar(client, email_teste)
    auth = _login(client, email_teste)
    token = auth["Authorization"].removeprefix("Bearer ")
    dados = PyJWTTokenService(settings.JWT_SECRET_KEY).verificar_token(token)

    client.post("/auth/logout", headers=auth)
    app.dependency_overrides.clear()

    revogado = db_session.scalar(
        select(TokenRevogadoModel).where(TokenRevogadoModel.jti == dados.jti)
    )
    assert revogado is not None
    assert revogado.usuario_id == dados.usuario_id
    assert revogado.expira_em == dados.expira_em


def test_logout_sem_token_ou_com_token_invalido_retorna_401(db_session):
    client = _client_com_sessao_de_teste(db_session)

    sem_token = client.post("/auth/logout")
    invalido = client.post("/auth/logout", headers={"Authorization": "Bearer invalido"})
    app.dependency_overrides.clear()

    assert sem_token.status_code == 401
    assert invalido.status_code == 401


def test_token_expirado_e_recusado(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)
    _cadastrar(client, email_teste)
    usuario_id = client.get("/usuarios/me", headers=_login(client, email_teste)).json()["id"]
    expirado = PyJWTTokenService(settings.JWT_SECRET_KEY, expire_minutes=-1).gerar_token(
        usuario_id, versao_sessao=0
    )
    auth = {"Authorization": f"Bearer {expirado}"}

    me = client.get("/usuarios/me", headers=auth)
    logout = client.post("/auth/logout", headers=auth)
    app.dependency_overrides.clear()

    assert me.status_code == 401
    assert logout.status_code == 401


def test_troca_de_senha_encerra_todas_as_sessoes(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)
    _cadastrar(client, email_teste)
    sessao_atual = _login(client, email_teste)
    outra_sessao = _login(client, email_teste)

    troca = client.patch(
        "/usuarios/me/senha",
        json={"senha_atual": "senha123", "senha_nova": "senhaNova456"},
        headers=sessao_atual,
    )
    me_atual = client.get("/usuarios/me", headers=sessao_atual)
    me_outra = client.get("/usuarios/me", headers=outra_sessao)
    me_nova = client.get("/usuarios/me", headers=_login(client, email_teste, "senhaNova456"))
    app.dependency_overrides.clear()

    assert troca.status_code == 204
    assert me_atual.status_code == 401
    assert me_outra.status_code == 401
    assert me_nova.status_code == 200


def test_troca_de_senha_recusada_mantem_as_sessoes(db_session, email_teste):
    client = _client_com_sessao_de_teste(db_session)
    _cadastrar(client, email_teste)
    auth = _login(client, email_teste)

    troca = client.patch(
        "/usuarios/me/senha",
        json={"senha_atual": "errada", "senha_nova": "senhaNova456"},
        headers=auth,
    )
    me = client.get("/usuarios/me", headers=auth)
    app.dependency_overrides.clear()

    assert troca.status_code == 400
    assert me.status_code == 200
