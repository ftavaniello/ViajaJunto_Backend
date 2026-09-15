import pytest

from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.application.use_cases.criar_usuario import CriarUsuario


def test_cria_usuario_com_sucesso():
    criar_usuario = CriarUsuario(UsuarioRepositoryMemory())

    usuario = criar_usuario.execute(
        nome="Livia",
        email="livia@example.com",
        senha_hash="hash123",
    )

    assert usuario.id == 1
    assert usuario.nome == "Livia"
    assert usuario.email == "livia@example.com"


def test_nao_permite_email_duplicado():
    criar_usuario = CriarUsuario(UsuarioRepositoryMemory())
    criar_usuario.execute(nome="Livia", email="livia@example.com", senha_hash="hash123")

    with pytest.raises(ValueError, match="Já existe um usuário com este email"):
        criar_usuario.execute(
            nome="Livia 2", email="livia@example.com", senha_hash="hash456"
        )
