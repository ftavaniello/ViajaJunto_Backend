import pytest

from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.adapters.outbound.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.application.use_cases.criar_usuario import CriarUsuario


def test_cria_usuario_com_sucesso():
    criar_usuario = CriarUsuario(UsuarioRepositoryMemory(), BcryptPasswordHasher())

    usuario = criar_usuario.execute(
        nome="Livia",
        email="livia@example.com",
        senha="senha123",
    )

    assert usuario.id == 1
    assert usuario.nome == "Livia"
    assert usuario.email == "livia@example.com"
    assert usuario.senha_hash != "senha123"


def test_nao_permite_email_duplicado():
    criar_usuario = CriarUsuario(UsuarioRepositoryMemory(), BcryptPasswordHasher())
    criar_usuario.execute(nome="Livia", email="livia@example.com", senha="senha123")

    with pytest.raises(ValueError, match="Já existe um usuário com este email"):
        criar_usuario.execute(nome="Livia 2", email="livia@example.com", senha="senha456")
