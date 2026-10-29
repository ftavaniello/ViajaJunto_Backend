from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.excluir_usuario import ExcluirUsuario
from tests.application.fakes import FakePasswordHasher


def test_exclui_usuario_existente():
    repository = UsuarioRepositoryMemory()
    CriarUsuario(repository, FakePasswordHasher(), UnitOfWorkMemory()).execute(
        nome="Livia", email="livia@example.com", senha="senha123"
    )

    ExcluirUsuario(repository, UnitOfWorkMemory()).execute(usuario_id=1)

    assert repository.buscar_por_id(1) is None


def test_excluir_usuario_inexistente_nao_levanta_erro():
    repository = UsuarioRepositoryMemory()

    ExcluirUsuario(repository, UnitOfWorkMemory()).execute(usuario_id=999)
