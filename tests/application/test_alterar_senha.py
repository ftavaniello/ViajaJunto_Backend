import pytest

from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.adapters.outbound.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.application.use_cases.alterar_senha import AlterarSenha
from app.application.use_cases.criar_usuario import CriarUsuario


def _repository_com_usuario() -> UsuarioRepositoryMemory:
    repository = UsuarioRepositoryMemory()
    CriarUsuario(repository, BcryptPasswordHasher()).execute(
        nome="Livia",
        email="livia@example.com",
        senha="senha123",
    )
    return repository


def test_altera_senha_com_sucesso():
    repository = _repository_com_usuario()
    password_hasher = BcryptPasswordHasher()

    AlterarSenha(repository, password_hasher).execute(
        usuario_id=1, senha_atual="senha123", senha_nova="senhaNova456"
    )

    usuario = repository.buscar_por_id(1)
    assert password_hasher.verificar("senhaNova456", usuario.senha_hash)
    assert not password_hasher.verificar("senha123", usuario.senha_hash)


def test_rejeita_senha_atual_incorreta():
    repository = _repository_com_usuario()

    with pytest.raises(ValueError, match="Senha atual incorreta"):
        AlterarSenha(repository, BcryptPasswordHasher()).execute(
            usuario_id=1, senha_atual="errada", senha_nova="senhaNova456"
        )
