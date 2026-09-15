from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.domain.entities.usuario import Usuario


def test_salvar_persiste_e_gera_id(db_session, email_teste):
    repository = SQLAlchemyUsuarioRepository(db_session)

    usuario = repository.salvar(
        Usuario(nome="Livia", email=email_teste, senha_hash="hash123")
    )

    assert usuario.id is not None


def test_buscar_por_id_encontra_usuario_salvo(db_session, email_teste):
    repository = SQLAlchemyUsuarioRepository(db_session)
    salvo = repository.salvar(
        Usuario(nome="Livia", email=email_teste, senha_hash="hash123")
    )

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
