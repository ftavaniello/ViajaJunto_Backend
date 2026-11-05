import pytest

from app.adapters.inbound.cli.seed_demo import EMAIL_DEMO, SENHA_DEMO, semear_usuario_demo
from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.application.use_cases.criar_usuario import CriarUsuario
from app.domain.entities.usuario import Usuario
from app.infrastructure.config import carregar_settings
from tests.application.fakes import FakePasswordHasher

DESENVOLVIMENTO = carregar_settings({"APP_ENV": "development"})


def test_seed_cria_conta_de_demonstracao_em_desenvolvimento():
    repository = UsuarioRepositoryMemory()

    mensagem = semear_usuario_demo(
        CriarUsuario(repository, FakePasswordHasher(), UnitOfWorkMemory()), DESENVOLVIMENTO
    )

    assert "criada" in mensagem
    assert SENHA_DEMO not in mensagem
    usuario = repository.buscar_por_email(EMAIL_DEMO)
    assert FakePasswordHasher().verificar(SENHA_DEMO, usuario.senha_hash)


def test_seed_nao_reescreve_conta_existente():
    repository = UsuarioRepositoryMemory()
    repository.salvar(Usuario(nome="Dono Real", email=EMAIL_DEMO, senha_hash="hash:outra-senha"))

    mensagem = semear_usuario_demo(
        CriarUsuario(repository, FakePasswordHasher(), UnitOfWorkMemory()), DESENVOLVIMENTO
    )

    assert "mantida sem alterações" in mensagem
    usuario = repository.buscar_por_email(EMAIL_DEMO)
    assert usuario.nome == "Dono Real"
    assert usuario.senha_hash == "hash:outra-senha"
    assert repository.contar() == 1


@pytest.mark.parametrize("app_env", ["production", "staging"])
def test_seed_e_bloqueado_fora_do_desenvolvimento(app_env):
    repository = UsuarioRepositoryMemory()
    config = carregar_settings({"APP_ENV": app_env, "JWT_SECRET_KEY": "x" * 40})

    caso = CriarUsuario(repository, FakePasswordHasher(), UnitOfWorkMemory())
    with pytest.raises(PermissionError):
        semear_usuario_demo(caso, config)

    assert repository.contar() == 0
