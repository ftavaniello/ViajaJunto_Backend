"""Monta adaptadores e injeta portas nos casos de uso.

Repositorios e UnitOfWork de uma requisicao recebem a mesma Session, para que as
gravacoes de um caso de uso fiquem na mesma transacao.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.membro_viagem_repository_sqlalchemy import (
    SQLAlchemyMembroViagemRepository,
)
from app.adapters.outbound.persistence.token_recuperacao_senha_repository_sqlalchemy import (
    SQLAlchemyTokenRecuperacaoSenhaRepository,
)
from app.adapters.outbound.persistence.token_revogado_repository_sqlalchemy import (
    SQLAlchemyTokenRevogadoRepository,
)
from app.adapters.outbound.persistence.unit_of_work_sqlalchemy import SQLAlchemyUnitOfWork
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.persistence.viagem_repository_sqlalchemy import (
    SQLAlchemyViagemRepository,
)
from app.adapters.outbound.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.adapters.outbound.security.pyjwt_token_service import PyJWTTokenService
from app.application.acesso_viagem import PoliticaAcessoViagem
from app.application.use_cases.alterar_senha import AlterarSenha
from app.application.use_cases.atualizar_usuario import AtualizarUsuario
from app.application.use_cases.atualizar_viagem import AtualizarViagem
from app.application.use_cases.autenticar_usuario import AutenticarUsuario
from app.application.use_cases.consultar_resumo_usuarios import ConsultarResumoUsuarios
from app.application.use_cases.consultar_usuario_autenticado import ConsultarUsuarioAutenticado
from app.application.use_cases.consultar_viagem import ConsultarViagem
from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.criar_viagem import CriarViagem
from app.application.use_cases.encerrar_sessao import EncerrarSessao
from app.application.use_cases.excluir_usuario import ExcluirUsuario
from app.application.use_cases.excluir_viagem import ExcluirViagem
from app.application.use_cases.listar_viagens import ListarViagens
from app.application.use_cases.redefinir_senha import RedefinirSenha
from app.application.use_cases.solicitar_recuperacao_senha import SolicitarRecuperacaoSenha
from app.domain.ports.email_sender import EmailSender
from app.domain.ports.token_service import TokenService
from app.domain.ports.total_usuarios_cache import TotalUsuariosCache
from app.infrastructure.cache import get_total_usuarios_cache
from app.infrastructure.config import settings
from app.infrastructure.database import get_db
from app.infrastructure.email import get_email_sender


def get_token_service() -> TokenService:
    return PyJWTTokenService(
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        expire_minutes=settings.JWT_EXPIRE_MINUTES,
    )


def get_criar_usuario(
    db: Session = Depends(get_db),
    cache: TotalUsuariosCache = Depends(get_total_usuarios_cache),
) -> CriarUsuario:
    return CriarUsuario(
        SQLAlchemyUsuarioRepository(db), BcryptPasswordHasher(), SQLAlchemyUnitOfWork(db), cache
    )


def get_excluir_usuario(
    db: Session = Depends(get_db),
    cache: TotalUsuariosCache = Depends(get_total_usuarios_cache),
) -> ExcluirUsuario:
    return ExcluirUsuario(SQLAlchemyUsuarioRepository(db), SQLAlchemyUnitOfWork(db), cache)


def get_atualizar_usuario(db: Session = Depends(get_db)) -> AtualizarUsuario:
    return AtualizarUsuario(SQLAlchemyUsuarioRepository(db), SQLAlchemyUnitOfWork(db))


def get_alterar_senha(db: Session = Depends(get_db)) -> AlterarSenha:
    return AlterarSenha(
        SQLAlchemyUsuarioRepository(db), BcryptPasswordHasher(), SQLAlchemyUnitOfWork(db)
    )


def get_autenticar_usuario(
    db: Session = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
) -> AutenticarUsuario:
    return AutenticarUsuario(SQLAlchemyUsuarioRepository(db), BcryptPasswordHasher(), token_service)


def get_consultar_usuario_autenticado(
    db: Session = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
) -> ConsultarUsuarioAutenticado:
    return ConsultarUsuarioAutenticado(
        SQLAlchemyUsuarioRepository(db), token_service, SQLAlchemyTokenRevogadoRepository(db)
    )


def get_encerrar_sessao(
    db: Session = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
) -> EncerrarSessao:
    return EncerrarSessao(
        token_service, SQLAlchemyTokenRevogadoRepository(db), SQLAlchemyUnitOfWork(db)
    )


def get_consultar_resumo(
    db: Session = Depends(get_db),
    cache: TotalUsuariosCache = Depends(get_total_usuarios_cache),
) -> ConsultarResumoUsuarios:
    return ConsultarResumoUsuarios(SQLAlchemyUsuarioRepository(db), cache)


def _politica_acesso_viagem(db: Session) -> PoliticaAcessoViagem:
    return PoliticaAcessoViagem(
        SQLAlchemyViagemRepository(db), SQLAlchemyMembroViagemRepository(db)
    )


def get_criar_viagem(db: Session = Depends(get_db)) -> CriarViagem:
    return CriarViagem(SQLAlchemyViagemRepository(db), SQLAlchemyUnitOfWork(db))


def get_listar_viagens(db: Session = Depends(get_db)) -> ListarViagens:
    return ListarViagens(SQLAlchemyViagemRepository(db))


def get_consultar_viagem(db: Session = Depends(get_db)) -> ConsultarViagem:
    return ConsultarViagem(_politica_acesso_viagem(db))


def get_atualizar_viagem(db: Session = Depends(get_db)) -> AtualizarViagem:
    return AtualizarViagem(
        SQLAlchemyViagemRepository(db), _politica_acesso_viagem(db), SQLAlchemyUnitOfWork(db)
    )


def get_excluir_viagem(db: Session = Depends(get_db)) -> ExcluirViagem:
    return ExcluirViagem(
        SQLAlchemyViagemRepository(db), _politica_acesso_viagem(db), SQLAlchemyUnitOfWork(db)
    )


def get_solicitar_recuperacao_senha(
    db: Session = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
) -> SolicitarRecuperacaoSenha:
    return SolicitarRecuperacaoSenha(
        SQLAlchemyUsuarioRepository(db),
        SQLAlchemyTokenRecuperacaoSenhaRepository(db),
        email_sender,
        SQLAlchemyUnitOfWork(db),
        url_redefinicao=settings.RECUPERACAO_SENHA_URL,
    )


def get_redefinir_senha(db: Session = Depends(get_db)) -> RedefinirSenha:
    return RedefinirSenha(
        SQLAlchemyUsuarioRepository(db),
        SQLAlchemyTokenRecuperacaoSenhaRepository(db),
        BcryptPasswordHasher(),
        SQLAlchemyUnitOfWork(db),
    )
