from datetime import datetime, timedelta, timezone

from app.adapters.outbound.persistence.token_revogado_model import TokenRevogadoModel
from app.adapters.outbound.persistence.token_revogado_repository_sqlalchemy import (
    SQLAlchemyTokenRevogadoRepository,
)
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.domain.entities.usuario import Usuario


def _usuario_id(db_session, email: str) -> int:
    return SQLAlchemyUsuarioRepository(db_session).salvar(
        Usuario(nome="Livia", email=email, senha_hash="hash")
    ).id


def _daqui(minutos: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutos)


def test_token_revogado_e_reconhecido(db_session, email_teste):
    repository = SQLAlchemyTokenRevogadoRepository(db_session)
    usuario_id = _usuario_id(db_session, email_teste)

    repository.revogar("jti-revogado", usuario_id, _daqui(30))

    assert repository.esta_revogado("jti-revogado")
    assert not repository.esta_revogado("jti-ativo")


def test_revogar_duas_vezes_e_idempotente(db_session, email_teste):
    repository = SQLAlchemyTokenRevogadoRepository(db_session)
    usuario_id = _usuario_id(db_session, email_teste)

    repository.revogar("jti-repetido", usuario_id, _daqui(30))
    repository.revogar("jti-repetido", usuario_id, _daqui(30))

    assert repository.esta_revogado("jti-repetido")


def test_revogar_remove_revogacoes_ja_expiradas(db_session, email_teste):
    repository = SQLAlchemyTokenRevogadoRepository(db_session)
    usuario_id = _usuario_id(db_session, email_teste)
    repository.revogar("jti-antigo", usuario_id, _daqui(-1))

    repository.revogar("jti-novo", usuario_id, _daqui(30))

    assert not repository.esta_revogado("jti-antigo")
    assert repository.esta_revogado("jti-novo")


def test_excluir_usuario_remove_suas_revogacoes(db_session, email_teste):
    repository = SQLAlchemyTokenRevogadoRepository(db_session)
    usuarios = SQLAlchemyUsuarioRepository(db_session)
    usuario_id = _usuario_id(db_session, email_teste)
    repository.revogar("jti-da-conta", usuario_id, _daqui(30))

    usuarios.deletar(usuario_id)
    db_session.expire_all()

    assert db_session.get(TokenRevogadoModel, "jti-da-conta") is None


def test_versao_sessao_e_persistida(db_session, email_teste):
    usuarios = SQLAlchemyUsuarioRepository(db_session)
    salvo = usuarios.salvar(Usuario(nome="Livia", email=email_teste, senha_hash="hash"))
    assert salvo.versao_sessao == 0

    salvo.versao_sessao = 2
    usuarios.salvar(salvo)

    assert usuarios.buscar_por_id(salvo.id).versao_sessao == 2
