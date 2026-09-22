from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.adapters.outbound.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.excluir_usuario import ExcluirUsuario


def test_exclui_usuario_existente():
    repository = UsuarioRepositoryMemory()
    CriarUsuario(repository, BcryptPasswordHasher()).execute(
        nome="Livia", email="livia@example.com", senha="senha123"
    )

    ExcluirUsuario(repository).execute(usuario_id=1)

    assert repository.buscar_por_id(1) is None


def test_excluir_usuario_inexistente_nao_levanta_erro():
    repository = UsuarioRepositoryMemory()

    ExcluirUsuario(repository).execute(usuario_id=999)
