"""Monta adaptadores e injeta portas nos casos de uso."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.adapters.outbound.security.pyjwt_token_service import PyJWTTokenService
from app.application.use_cases.alterar_senha import AlterarSenha
from app.application.use_cases.atualizar_usuario import AtualizarUsuario
from app.application.use_cases.autenticar_usuario import AutenticarUsuario
from app.application.use_cases.consultar_resumo_usuarios import ConsultarResumoUsuarios
from app.application.use_cases.consultar_usuario_autenticado import ConsultarUsuarioAutenticado
from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.excluir_usuario import ExcluirUsuario
from app.domain.ports.total_usuarios_cache import TotalUsuariosCache
from app.infrastructure.cache import get_total_usuarios_cache
from app.infrastructure.database import get_db


def get_criar_usuario(
    db: Session = Depends(get_db),
    cache: TotalUsuariosCache = Depends(get_total_usuarios_cache),
) -> CriarUsuario:
    return CriarUsuario(SQLAlchemyUsuarioRepository(db), BcryptPasswordHasher(), cache)


def get_excluir_usuario(
    db: Session = Depends(get_db),
    cache: TotalUsuariosCache = Depends(get_total_usuarios_cache),
) -> ExcluirUsuario:
    return ExcluirUsuario(SQLAlchemyUsuarioRepository(db), cache)


def get_atualizar_usuario(db: Session = Depends(get_db)) -> AtualizarUsuario:
    return AtualizarUsuario(SQLAlchemyUsuarioRepository(db))


def get_alterar_senha(db: Session = Depends(get_db)) -> AlterarSenha:
    return AlterarSenha(SQLAlchemyUsuarioRepository(db), BcryptPasswordHasher())


def get_autenticar_usuario(db: Session = Depends(get_db)) -> AutenticarUsuario:
    return AutenticarUsuario(
        SQLAlchemyUsuarioRepository(db), BcryptPasswordHasher(), PyJWTTokenService(),
    )


def get_consultar_usuario_autenticado(
    db: Session = Depends(get_db),
) -> ConsultarUsuarioAutenticado:
    return ConsultarUsuarioAutenticado(SQLAlchemyUsuarioRepository(db), PyJWTTokenService())


def get_consultar_resumo(
    db: Session = Depends(get_db),
    cache: TotalUsuariosCache = Depends(get_total_usuarios_cache),
) -> ConsultarResumoUsuarios:
    return ConsultarResumoUsuarios(SQLAlchemyUsuarioRepository(db), cache)
