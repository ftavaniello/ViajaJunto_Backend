import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.adapters.outbound.persistence.unit_of_work_sqlalchemy import SQLAlchemyUnitOfWork
from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.application.use_cases.criar_usuario import CriarUsuario
from app.domain.entities.usuario import Usuario
from app.domain.errors import EmailDuplicado
from app.infrastructure.database import SessionLocal
from tests.application.fakes import FakePasswordHasher


def test_salvar_persiste_e_gera_id(db_session, email_teste):
    repository = SQLAlchemyUsuarioRepository(db_session)

    usuario = repository.salvar(Usuario(nome="Livia", email=email_teste, senha_hash="hash123"))

    assert usuario.id is not None


def test_buscar_por_id_encontra_usuario_salvo(db_session, email_teste):
    repository = SQLAlchemyUsuarioRepository(db_session)
    salvo = repository.salvar(Usuario(nome="Livia", email=email_teste, senha_hash="hash123"))

    encontrado = repository.buscar_por_id(salvo.id)

    assert encontrado is not None
    assert encontrado.email == email_teste


def test_buscar_por_email_encontra_usuario_salvo(db_session, email_teste):
    repository = SQLAlchemyUsuarioRepository(db_session)
    repository.salvar(Usuario(nome="Livia", email=email_teste, senha_hash="hash123"))

    encontrado = repository.buscar_por_email(email_teste)

    assert encontrado is not None
    assert encontrado.email == email_teste


def test_buscar_por_email_inexistente_retorna_none(db_session):
    repository = SQLAlchemyUsuarioRepository(db_session)

    assert repository.buscar_por_email("nao-existe@example.com") is None


def test_deletar_remove_usuario_salvo(db_session, email_teste):
    repository = SQLAlchemyUsuarioRepository(db_session)
    salvo = repository.salvar(Usuario(nome="Livia", email=email_teste, senha_hash="hash123"))

    repository.deletar(salvo.id)

    assert repository.buscar_por_id(salvo.id) is None


def test_email_duplicado_no_banco_vira_erro_de_dominio(db_session, email_teste):
    repository = SQLAlchemyUsuarioRepository(db_session)
    uow = SQLAlchemyUnitOfWork(db_session)
    with uow:
        repository.salvar(Usuario(nome="Livia", email=email_teste, senha_hash="hash123"))
        uow.commit()

    # Simula a corrida: o caso de uso nao viu o primeiro registro, mas o banco rejeita.
    with pytest.raises(EmailDuplicado):
        with uow:
            repository.salvar(Usuario(nome="Outra", email=email_teste, senha_hash="hash456"))
            uow.commit()

    assert repository.buscar_por_email(email_teste) is not None


def test_salvar_preenche_criado_em_e_atualizacao_nao_o_altera(db_session, email_teste):
    repository = SQLAlchemyUsuarioRepository(db_session)
    salvo = repository.salvar(Usuario(nome="Livia", email=email_teste, senha_hash="hash123"))

    assert salvo.criado_em is not None
    assert salvo.criado_em.tzinfo is not None

    salvo.nome = "Livia Bampi"
    atualizado = repository.salvar(salvo)

    assert atualizado.criado_em == salvo.criado_em


def test_cadastros_concorrentes_com_mesmo_email_um_vira_erro_controlado(db_session, email_teste):
    outra_sessao = SessionLocal()

    class RepositorioQueSofreCorrida(SQLAlchemyUsuarioRepository):
        def buscar_por_email(self, email):
            resultado = super().buscar_por_email(email)
            # Simula uma requisição que confirma o cadastro após a checagem prévia.
            SQLAlchemyUsuarioRepository(outra_sessao).salvar(
                Usuario(nome="Concorrente", email=email, senha_hash="hash-concorrente")
            )
            outra_sessao.commit()
            return resultado

    try:
        criar_usuario = CriarUsuario(
            RepositorioQueSofreCorrida(db_session),
            FakePasswordHasher(),
            SQLAlchemyUnitOfWork(db_session),
        )
        with pytest.raises(EmailDuplicado):
            criar_usuario.execute(nome="Livia", email=email_teste, senha="senha123")
        vencedor = SQLAlchemyUsuarioRepository(db_session).buscar_por_email(email_teste)
        assert vencedor.nome == "Concorrente"
    finally:
        # A segunda sessão confirmou fora do rollback da fixture; limpa só seu registro.
        db_session.rollback()
        outra_sessao.rollback()
        outra_sessao.execute(delete(UsuarioModel).where(UsuarioModel.email == email_teste))
        outra_sessao.commit()
        outra_sessao.close()


def test_outra_violacao_de_integridade_nao_e_mascarada_como_email_duplicado(
    db_session, email_teste
):
    repository = SQLAlchemyUsuarioRepository(db_session)
    usuario = Usuario(nome="Livia", email=email_teste, senha_hash="hash123")
    usuario.nome = None  # burla a entidade para violar o NOT NULL do banco

    with pytest.raises(IntegrityError) as erro:
        repository.salvar(usuario)

    assert not isinstance(erro.value, EmailDuplicado)
