"""Contrato da recuperacao de senha (RF03): ver docs/recuperacao-de-senha.md."""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.adapters.outbound.email.email_sender_memory import EmailSenderMemory
from app.adapters.outbound.persistence.recuperacao_senha_model import TokenRecuperacaoSenhaModel
from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.domain.entities.token_recuperacao_senha import TokenRecuperacaoSenha
from app.infrastructure.config import settings
from app.infrastructure.database import get_db
from app.infrastructure.email import get_email_sender
from app.main import app


@pytest.fixture
def email_sender() -> EmailSenderMemory:
    return EmailSenderMemory()


@pytest.fixture
def client(db_session, email_sender):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_email_sender] = lambda: email_sender
    yield TestClient(app)
    app.dependency_overrides.clear()


def _cadastrar(client: TestClient, email: str) -> None:
    response = client.post("/usuarios", json={"nome": "Livia", "email": email, "senha": "senha123"})
    assert response.status_code == 201


def _login(client: TestClient, email: str, senha: str):
    return client.post("/auth/login", json={"email": email, "senha": senha})


def _token_do_email(email_sender: EmailSenderMemory) -> str:
    link = next(
        linha for linha in email_sender.enviados[-1].corpo.splitlines()
        if linha.startswith(settings.RECUPERACAO_SENHA_URL)
    )
    return parse_qs(urlparse(link).query)["token"][0]


def _solicitar_token(client, email_sender, email) -> str:
    response = client.post("/auth/recuperar-senha", json={"email": email})
    assert response.status_code == 202
    return _token_do_email(email_sender)


def test_fluxo_completo_de_recuperacao(client, email_sender, email_teste):
    _cadastrar(client, email_teste)

    solicitacao = client.post("/auth/recuperar-senha", json={"email": email_teste})
    token = _token_do_email(email_sender)
    redefinicao = client.post(
        "/auth/redefinir-senha", json={"token": token, "senha_nova": "senhaNova456"}
    )

    assert solicitacao.status_code == 202
    assert email_sender.enviados[0].destinatario == email_teste
    assert redefinicao.status_code == 204
    assert _login(client, email_teste, "senha123").status_code == 401
    assert _login(client, email_teste, "senhaNova456").status_code == 200


def test_resposta_nao_revela_se_o_email_esta_cadastrado(client, email_sender, email_teste):
    _cadastrar(client, email_teste)

    cadastrado = client.post("/auth/recuperar-senha", json={"email": email_teste})
    desconhecido = client.post(
        "/auth/recuperar-senha", json={"email": email_teste.replace("teste-", "nao-existe-")}
    )

    assert cadastrado.status_code == desconhecido.status_code == 202
    assert cadastrado.json() == desconhecido.json()
    assert len(email_sender.enviados) == 1


def test_falha_no_envio_retorna_a_mesma_resposta(client, email_sender, email_teste):
    _cadastrar(client, email_teste)
    email_sender.falhar = True

    response = client.post("/auth/recuperar-senha", json={"email": email_teste})

    assert response.status_code == 202
    assert response.json()["detail"].startswith("Se o email estiver cadastrado")


def test_banco_guarda_so_o_hash_do_token(client, email_sender, email_teste, db_session):
    _cadastrar(client, email_teste)
    token = _solicitar_token(client, email_sender, email_teste)

    registro = db_session.scalar(
        select(TokenRecuperacaoSenhaModel)
        .join(UsuarioModel, UsuarioModel.id == TokenRecuperacaoSenhaModel.usuario_id)
        .where(UsuarioModel.email == email_teste)
    )
    assert registro.token_hash == TokenRecuperacaoSenha.calcular_hash(token)
    assert registro.token_hash != token
    assert registro.usado_em is None
    restante = registro.expira_em - datetime.now(timezone.utc)
    assert timedelta(minutes=59) < restante <= timedelta(minutes=60)


def test_token_reutilizado_retorna_400(client, email_sender, email_teste):
    _cadastrar(client, email_teste)
    token = _solicitar_token(client, email_sender, email_teste)

    primeira = client.post(
        "/auth/redefinir-senha", json={"token": token, "senha_nova": "senhaNova456"}
    )
    segunda = client.post(
        "/auth/redefinir-senha", json={"token": token, "senha_nova": "outraSenha789"}
    )

    assert primeira.status_code == 204
    assert segunda.status_code == 400
    assert _login(client, email_teste, "senhaNova456").status_code == 200


def test_token_vencido_retorna_400(client, email_sender, email_teste, db_session):
    _cadastrar(client, email_teste)
    token = _solicitar_token(client, email_sender, email_teste)
    db_session.execute(
        update(TokenRecuperacaoSenhaModel)
        .where(TokenRecuperacaoSenhaModel.token_hash == TokenRecuperacaoSenha.calcular_hash(token))
        .values(expira_em=datetime.now(timezone.utc) - timedelta(seconds=1))
    )
    db_session.commit()

    response = client.post(
        "/auth/redefinir-senha", json={"token": token, "senha_nova": "senhaNova456"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Token de recuperação inválido ou expirado"
    assert _login(client, email_teste, "senha123").status_code == 200


def test_token_invalido_retorna_400(client):
    response = client.post(
        "/auth/redefinir-senha", json={"token": "token-inventado", "senha_nova": "senhaNova456"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Token de recuperação inválido ou expirado"


def test_link_anterior_deixa_de_valer_apos_novo_pedido(client, email_sender, email_teste):
    _cadastrar(client, email_teste)
    primeiro = _solicitar_token(client, email_sender, email_teste)
    segundo = _solicitar_token(client, email_sender, email_teste)

    antigo = client.post(
        "/auth/redefinir-senha", json={"token": primeiro, "senha_nova": "senhaNova456"}
    )
    novo = client.post(
        "/auth/redefinir-senha", json={"token": segundo, "senha_nova": "senhaNova456"}
    )

    assert antigo.status_code == 400
    assert novo.status_code == 204


def test_senha_nova_curta_retorna_422_e_nao_gasta_o_token(client, email_sender, email_teste):
    _cadastrar(client, email_teste)
    token = _solicitar_token(client, email_sender, email_teste)

    curta = client.post("/auth/redefinir-senha", json={"token": token, "senha_nova": "curta"})
    valida = client.post(
        "/auth/redefinir-senha", json={"token": token, "senha_nova": "senhaNova456"}
    )

    assert curta.status_code == 422
    assert valida.status_code == 204


def test_redefinicao_encerra_as_sessoes_abertas(client, email_sender, email_teste):
    _cadastrar(client, email_teste)
    access_token = _login(client, email_teste, "senha123").json()["access_token"]
    sessao = {"Authorization": f"Bearer {access_token}"}
    token = _solicitar_token(client, email_sender, email_teste)

    client.post("/auth/redefinir-senha", json={"token": token, "senha_nova": "senhaNova456"})

    assert client.get("/usuarios/me", headers=sessao).status_code == 401


def test_endpoints_de_recuperacao_sao_publicos(client):
    # Sem Authorization: nao exigem token, ao contrario das rotas de conta.
    solicitacao = client.post("/auth/recuperar-senha", json={"email": "alguem@example.com"})
    redefinicao = client.post(
        "/auth/redefinir-senha", json={"token": "x", "senha_nova": "senhaNova456"}
    )

    assert solicitacao.status_code == 202
    assert redefinicao.status_code == 400


def test_email_mal_formado_retorna_422(client):
    response = client.post("/auth/recuperar-senha", json={"email": "nao-e-email"})

    assert response.status_code == 422
