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
from app.domain.ports.token_service import TokenService
from app.domain.ports.total_usuarios_cache import TotalUsuariosCache
from app.infrastructure.cache import get_total_usuarios_cache
from app.infrastructure.config import settings
from app.infrastructure.database import get_db


def get_token_service() -> TokenService:
    return PyJWTTokenService(
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        expire_minutes=settings.JWT_EXPIRE_MINUTES,
    )


def montar_criar_usuario(db: Session, cache: TotalUsuariosCache) -> CriarUsuario:
    """Composicao reutilizada pela API e por adaptadores de entrada fora do HTTP."""
    return CriarUsuario(SQLAlchemyUsuarioRepository(db), BcryptPasswordHasher(), cache)


def get_criar_usuario(
    db: Session = Depends(get_db),
    cache: TotalUsuariosCache = Depends(get_total_usuarios_cache),
) -> CriarUsuario:
    return montar_criar_usuario(db, cache)


def get_excluir_usuario(
    db: Session = Depends(get_db),
    cache: TotalUsuariosCache = Depends(get_total_usuarios_cache),
) -> ExcluirUsuario:
    return ExcluirUsuario(SQLAlchemyUsuarioRepository(db), cache)


def get_atualizar_usuario(db: Session = Depends(get_db)) -> AtualizarUsuario:
    return AtualizarUsuario(SQLAlchemyUsuarioRepository(db))


def get_alterar_senha(db: Session = Depends(get_db)) -> AlterarSenha:
    return AlterarSenha(SQLAlchemyUsuarioRepository(db), BcryptPasswordHasher())


def get_autenticar_usuario(
    db: Session = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
) -> AutenticarUsuario:
    return AutenticarUsuario(SQLAlchemyUsuarioRepository(db), BcryptPasswordHasher(), token_service)


def get_consultar_usuario_autenticado(
    db: Session = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
) -> ConsultarUsuarioAutenticado:
    return ConsultarUsuarioAutenticado(SQLAlchemyUsuarioRepository(db), token_service)


def get_consultar_resumo(
    db: Session = Depends(get_db),
    cache: TotalUsuariosCache = Depends(get_total_usuarios_cache),
) -> ConsultarResumoUsuarios:
    return ConsultarResumoUsuarios(SQLAlchemyUsuarioRepository(db), cache)
