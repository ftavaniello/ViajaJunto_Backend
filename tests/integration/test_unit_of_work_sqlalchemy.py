import pytest

from app.adapters.outbound.persistence.unit_of_work_sqlalchemy import SQLAlchemyUnitOfWork
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.domain.entities.usuario import Usuario
from app.domain.errors import EmailDuplicado


def test_falha_na_segunda_gravacao_desfaz_a_primeira(db_session, email_teste):
    repository = SQLAlchemyUsuarioRepository(db_session)
    uow = SQLAlchemyUnitOfWork(db_session)
    with uow:
        existente = repository.salvar(Usuario(nome="Existente", email=email_teste,
                                              senha_hash="hash"))
        uow.commit()
    novo_email = email_teste.replace("@", "-novo@")

    with pytest.raises(EmailDuplicado):
        with uow:
            primeiro = repository.salvar(
                Usuario(nome="Primeiro", email=novo_email, senha_hash="hash")
            )
            # A primeira gravacao ja chegou ao banco (tem id), mas ainda nao foi confirmada.
            assert primeiro.id is not None
            # A segunda viola a unicidade do email e falha.
            repository.salvar(Usuario(nome="Segundo", email=email_teste, senha_hash="hash"))
            uow.commit()

    assert repository.buscar_por_id(primeiro.id) is None
    assert repository.buscar_por_email(novo_email) is None
    # O que foi confirmado antes da operacao nao e afetado.
    assert repository.buscar_por_id(existente.id) is not None


def test_commit_confirma_todas_as_gravacoes(db_session, email_teste):
    repository = SQLAlchemyUsuarioRepository(db_session)
    uow = SQLAlchemyUnitOfWork(db_session)
    outro_email = email_teste.replace("@", "-outro@")

    with uow:
        repository.salvar(Usuario(nome="Primeiro", email=email_teste, senha_hash="hash"))
        repository.salvar(Usuario(nome="Segundo", email=outro_email, senha_hash="hash"))
        uow.commit()
    db_session.expire_all()

    assert repository.buscar_por_email(email_teste) is not None
    assert repository.buscar_por_email(outro_email) is not None


def test_sair_sem_commit_desfaz_as_gravacoes(db_session, email_teste):
    repository = SQLAlchemyUsuarioRepository(db_session)

    with SQLAlchemyUnitOfWork(db_session):
        repository.salvar(Usuario(nome="Livia", email=email_teste, senha_hash="hash"))

    assert repository.buscar_por_email(email_teste) is None
