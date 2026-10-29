"""Casos de uso que gravam confirmam a transacao no sucesso e a desfazem na falha."""
from unittest.mock import Mock

import pytest

from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.application.use_cases.alterar_senha import AlterarSenha
from app.application.use_cases.atualizar_usuario import AtualizarUsuario
from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.excluir_usuario import ExcluirUsuario
from app.domain.errors import EmailDuplicado
from tests.application.fakes import FakePasswordHasher


def _repository_com_usuario() -> UsuarioRepositoryMemory:
    repository = UsuarioRepositoryMemory()
    CriarUsuario(repository, FakePasswordHasher(), UnitOfWorkMemory()).execute(
        nome="Livia", email="livia@example.com", senha="senha123"
    )
    return repository


def test_criar_usuario_confirma_a_transacao():
    uow = UnitOfWorkMemory()

    CriarUsuario(UsuarioRepositoryMemory(), FakePasswordHasher(), uow).execute(
        nome="Livia", email="livia@example.com", senha="senha123"
    )

    assert (uow.commits, uow.rollbacks) == (1, 0)


def test_falha_ao_gravar_desfaz_a_transacao_sem_confirmar():
    repository = Mock(wraps=UsuarioRepositoryMemory())
    repository.salvar.side_effect = EmailDuplicado("Já existe um usuário com este email")
    uow = UnitOfWorkMemory()
    cache = Mock()

    with pytest.raises(EmailDuplicado):
        CriarUsuario(repository, FakePasswordHasher(), uow, cache).execute(
            nome="Livia", email="livia@example.com", senha="senha123"
        )

    assert (uow.commits, uow.rollbacks) == (0, 1)
    cache.invalidar.assert_not_called()


def test_cache_e_invalidado_somente_depois_do_commit():
    eventos = []
    uow = UnitOfWorkMemory()
    uow.commit = lambda: eventos.append("commit")
    cache = Mock()
    cache.invalidar.side_effect = lambda: eventos.append("invalidar")

    CriarUsuario(UsuarioRepositoryMemory(), FakePasswordHasher(), uow, cache).execute(
        nome="Livia", email="livia@example.com", senha="senha123"
    )

    assert eventos == ["commit", "invalidar"]


def test_atualizar_alterar_senha_e_excluir_confirmam_a_transacao():
    repository = _repository_com_usuario()
    uow = UnitOfWorkMemory()

    AtualizarUsuario(repository, uow).execute(usuario_id=1, nome="Livia Bampi", email=None)
    AlterarSenha(repository, FakePasswordHasher(), uow).execute(
        usuario_id=1, senha_atual="senha123", senha_nova="senhaNova456"
    )
    ExcluirUsuario(repository, uow).execute(usuario_id=1)

    assert (uow.commits, uow.rollbacks) == (3, 0)
