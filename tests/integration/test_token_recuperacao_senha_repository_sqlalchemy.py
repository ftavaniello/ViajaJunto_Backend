from datetime import datetime, timedelta, timezone

from app.adapters.outbound.persistence.token_recuperacao_senha_repository_sqlalchemy import (
    SQLAlchemyTokenRecuperacaoSenhaRepository,
)
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.domain.entities.token_recuperacao_senha import TokenRecuperacaoSenha
from app.domain.entities.usuario import Usuario

AGORA = datetime.now(timezone.utc)


def _usuario(db_session, email: str) -> Usuario:
    return SQLAlchemyUsuarioRepository(db_session).salvar(
        Usuario(nome="Livia", email=email, senha_hash="hash")
    )


def test_salva_busca_e_marca_uso(db_session, email_teste):
    usuario = _usuario(db_session, email_teste)
    repo = SQLAlchemyTokenRecuperacaoSenhaRepository(db_session)
    token, valor = TokenRecuperacaoSenha.emitir(usuario.id, AGORA, 60)

    salvo = repo.salvar(token)
    encontrado = repo.buscar_por_hash(TokenRecuperacaoSenha.calcular_hash(valor))

    assert salvo.id is not None
    assert encontrado.usuario_id == usuario.id
    assert encontrado.expira_em == AGORA + timedelta(minutes=60)
    assert encontrado.pode_ser_usado(AGORA)

    encontrado.marcar_usado(AGORA)
    repo.salvar(encontrado)
    db_session.commit()

    assert not repo.buscar_por_hash(token.token_hash).pode_ser_usado(AGORA)


def test_hash_desconhecido_retorna_none(db_session):
    repo = SQLAlchemyTokenRecuperacaoSenhaRepository(db_session)

    assert repo.buscar_por_hash("0" * 64) is None


def test_invalidar_pendentes_afeta_so_o_usuario_informado(db_session, email_teste):
    usuario = _usuario(db_session, email_teste)
    outro = _usuario(db_session, email_teste.replace("@", "-outro@"))
    repo = SQLAlchemyTokenRecuperacaoSenhaRepository(db_session)
    do_usuario, _ = TokenRecuperacaoSenha.emitir(usuario.id, AGORA, 60)
    do_outro, _ = TokenRecuperacaoSenha.emitir(outro.id, AGORA, 60)
    repo.salvar(do_usuario)
    repo.salvar(do_outro)

    repo.invalidar_pendentes(usuario.id, AGORA)
    db_session.commit()

    assert not repo.buscar_por_hash(do_usuario.token_hash).pode_ser_usado(AGORA)
    assert repo.buscar_por_hash(do_outro.token_hash).pode_ser_usado(AGORA)
