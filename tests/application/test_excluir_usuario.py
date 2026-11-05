from unittest.mock import Mock

import pytest

from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.excluir_usuario import ExcluirUsuario
from app.domain.errors import ContaComViagensCompartilhadas
from app.domain.ports.vinculos_conta_repository import VinculosContaRepository
from tests.application.fakes import FakePasswordHasher


def test_exclui_usuario_existente():
    repository = UsuarioRepositoryMemory()
    CriarUsuario(repository, FakePasswordHasher(), UnitOfWorkMemory()).execute(
        nome="Livia", email="livia@example.com", senha="senha123"
    )

    ExcluirUsuario(
        repository,
        UnitOfWorkMemory(),
        Mock(bloquear_e_verificar_colaboradores=Mock(return_value=False)),
    ).execute(usuario_id=1)

    assert repository.buscar_por_id(1) is None


def test_excluir_usuario_inexistente_nao_levanta_erro():
    repository = UsuarioRepositoryMemory()

    ExcluirUsuario(
        repository,
        UnitOfWorkMemory(),
        Mock(bloquear_e_verificar_colaboradores=Mock(return_value=False)),
    ).execute(usuario_id=999)


@pytest.mark.parametrize("compartilhada", [True, False])
def test_politica_e_cache_so_apos_commit(compartilhada):
    eventos = []
    repository = Mock()
    uow = UnitOfWorkMemory()
    uow.commit = Mock(side_effect=lambda: eventos.append("commit"))
    vinculos = Mock(spec=VinculosContaRepository)
    vinculos.bloquear_e_verificar_colaboradores.return_value = compartilhada
    cache = Mock()
    cache.invalidar.side_effect = lambda: eventos.append("cache")
    caso = ExcluirUsuario(repository, uow, vinculos, cache)
    if compartilhada:
        with pytest.raises(ContaComViagensCompartilhadas):
            caso.execute(1)
        repository.deletar.assert_not_called()
        assert eventos == []
        uow.commit.assert_not_called()
    else:
        caso.execute(1)
        repository.deletar.assert_called_once_with(1)
        assert eventos == ["commit", "cache"]
    vinculos.bloquear_e_verificar_colaboradores.assert_called_once_with(1)


def test_falha_no_commit_nao_invalida_cache():
    repository = Mock()
    uow = UnitOfWorkMemory()
    uow.commit = Mock(side_effect=RuntimeError("falha"))
    vinculos = Mock(bloquear_e_verificar_colaboradores=Mock(return_value=False))
    cache = Mock()
    with pytest.raises(RuntimeError, match="falha"):
        ExcluirUsuario(repository, uow, vinculos, cache).execute(1)
    cache.invalidar.assert_not_called()
    assert uow.rollbacks == 1
