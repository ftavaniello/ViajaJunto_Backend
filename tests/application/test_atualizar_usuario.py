import pytest

from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.application.use_cases.atualizar_usuario import AtualizarUsuario
from app.application.use_cases.criar_usuario import CriarUsuario
from app.domain.errors import EmailDuplicado
from tests.application.fakes import FakePasswordHasher, RepositorioComCorrida


def _repository_com_usuario() -> UsuarioRepositoryMemory:
    repository = UsuarioRepositoryMemory()
    CriarUsuario(repository, FakePasswordHasher(), UnitOfWorkMemory()).execute(
        nome="Livia",
        email="livia@example.com",
        senha="senha123",
    )
    return repository


def test_atualiza_nome_e_email():
    repository = _repository_com_usuario()

    usuario = AtualizarUsuario(repository, UnitOfWorkMemory()).execute(
        usuario_id=1, nome="Livia Bampi", email="livia.bampi@example.com"
    )

    assert usuario.nome == "Livia Bampi"
    assert usuario.email == "livia.bampi@example.com"


def test_campos_omitidos_permanecem_inalterados():
    repository = _repository_com_usuario()

    usuario = AtualizarUsuario(repository, UnitOfWorkMemory()).execute(
        usuario_id=1, nome=None, email=None
    )

    assert usuario.nome == "Livia"
    assert usuario.email == "livia@example.com"


def test_nao_permite_atualizar_para_email_de_outro_usuario():
    repository = _repository_com_usuario()
    CriarUsuario(repository, FakePasswordHasher(), UnitOfWorkMemory()).execute(
        nome="Outro", email="outro@example.com", senha="senha123"
    )

    with pytest.raises(ValueError, match="Já existe um usuário com este email"):
        AtualizarUsuario(repository, UnitOfWorkMemory()).execute(
            usuario_id=1, nome=None, email="outro@example.com"
        )


def test_usuario_inexistente_levanta_erro():
    repository = UsuarioRepositoryMemory()

    with pytest.raises(ValueError, match="Usuário não encontrado"):
        AtualizarUsuario(repository, UnitOfWorkMemory()).execute(
            usuario_id=999, nome="X", email=None
        )


def test_atualizacao_preserva_data_de_criacao():
    repository = _repository_com_usuario()
    criado_em = repository.buscar_por_id(1).criado_em

    usuario = AtualizarUsuario(repository, UnitOfWorkMemory()).execute(
        usuario_id=1, nome="Livia B", email=None
    )

    assert usuario.criado_em == criado_em


def test_troca_de_email_concorrente_vira_erro_controlado():
    repository = RepositorioComCorrida()
    criar_usuario = CriarUsuario(repository, FakePasswordHasher(), UnitOfWorkMemory())
    criar_usuario.execute(nome="Livia", email="livia@example.com", senha="senha123")
    criar_usuario.execute(nome="Outro", email="outro@example.com", senha="senha123")

    with pytest.raises(EmailDuplicado):
        AtualizarUsuario(repository, UnitOfWorkMemory()).execute(
            usuario_id=1, nome=None, email="outro@example.com"
        )

    assert repository.buscar_por_id(1).email == "livia@example.com"
