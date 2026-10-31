import pytest

from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.application.use_cases.criar_usuario import CriarUsuario
from app.domain.errors import EmailDuplicado
from tests.application.fakes import FakePasswordHasher, RepositorioComCorrida


def test_cria_usuario_com_sucesso():
    criar_usuario = CriarUsuario(UsuarioRepositoryMemory(), FakePasswordHasher())

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
    criar_usuario = CriarUsuario(UsuarioRepositoryMemory(), FakePasswordHasher())
    criar_usuario.execute(nome="Livia", email="livia@example.com", senha="senha123")

    with pytest.raises(ValueError, match="Já existe um usuário com este email"):
        criar_usuario.execute(nome="Livia 2", email="livia@example.com", senha="senha456")


def test_cadastro_registra_data_de_criacao():
    usuario = CriarUsuario(UsuarioRepositoryMemory(), FakePasswordHasher()).execute(
        nome="Livia", email="livia@example.com", senha="senha123"
    )

    assert usuario.criado_em is not None


def test_cadastro_concorrente_com_mesmo_email_vira_erro_controlado():
    repository = RepositorioComCorrida()
    criar_usuario = CriarUsuario(repository, FakePasswordHasher())
    criar_usuario.execute(nome="Livia", email="livia@example.com", senha="senha123")

    # A checagem previa nao ve o primeiro cadastro, mas o salvar e rejeitado.
    with pytest.raises(EmailDuplicado):
        criar_usuario.execute(nome="Livia 2", email="livia@example.com", senha="senha456")

    assert repository.contar() == 1
