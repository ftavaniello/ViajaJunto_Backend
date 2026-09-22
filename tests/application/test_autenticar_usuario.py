import pytest

from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.adapters.outbound.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.adapters.outbound.security.pyjwt_token_service import PyJWTTokenService
from app.application.use_cases.autenticar_usuario import AutenticarUsuario
from app.application.use_cases.criar_usuario import CriarUsuario


def _autenticar_usuario():
    repository = UsuarioRepositoryMemory()
    password_hasher = BcryptPasswordHasher()
    token_service = PyJWTTokenService()

    CriarUsuario(repository, password_hasher).execute(
        nome="Livia",
        email="livia@example.com",
        senha="senha123",
    )

    return AutenticarUsuario(repository, password_hasher, token_service), token_service


def test_autentica_com_credenciais_corretas_e_retorna_token_valido():
    autenticar_usuario, token_service = _autenticar_usuario()

    token = autenticar_usuario.execute(email="livia@example.com", senha="senha123")

    assert isinstance(token, str)
    assert token_service.verificar_token(token) == 1


def test_rejeita_senha_incorreta():
    autenticar_usuario, _ = _autenticar_usuario()

    with pytest.raises(ValueError, match="Email ou senha inválidos"):
        autenticar_usuario.execute(email="livia@example.com", senha="errada")


def test_rejeita_email_inexistente():
    autenticar_usuario, _ = _autenticar_usuario()

    with pytest.raises(ValueError, match="Email ou senha inválidos"):
        autenticar_usuario.execute(email="ninguem@example.com", senha="senha123")
