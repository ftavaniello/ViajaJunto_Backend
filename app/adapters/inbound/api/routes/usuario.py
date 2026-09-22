from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.adapters.inbound.api.schemas.usuario_schema import (
    AlterarSenhaRequest,
    AtualizarUsuarioRequest,
    CriarUsuarioRequest,
    UsuarioResponse,
)
from app.adapters.inbound.api.security import get_usuario_atual
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.application.use_cases.alterar_senha import AlterarSenha
from app.application.use_cases.atualizar_usuario import AtualizarUsuario
from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.excluir_usuario import ExcluirUsuario
from app.domain.entities.usuario import Usuario
from app.infrastructure.database import get_db


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
)


@router.post(
    "",
    response_model=UsuarioResponse,
    status_code=201,
    summary="Cria um novo usuário",
    description=(
        "Cadastra um novo usuário na plataforma. Endpoint público (não requer "
        "autenticação), já que é o ponto de entrada para obter uma conta. A senha "
        "enviada em texto puro é hasheada antes de ser persistida."
    ),
    responses={
        400: {"description": "Já existe um usuário com este email"},
    },
)
def criar(request: CriarUsuarioRequest, db: Session = Depends(get_db)):
    try:
        repository = SQLAlchemyUsuarioRepository(db)
        criar_usuario = CriarUsuario(repository, BcryptPasswordHasher())

        usuario = criar_usuario.execute(
            nome=request.nome,
            email=request.email,
            senha=request.senha,
        )

        return UsuarioResponse(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get(
    "/me",
    response_model=UsuarioResponse,
    summary="Retorna os dados do usuário autenticado",
    description=(
        "Requer um token JWT válido no header `Authorization: Bearer <access_token>`, "
        "obtido em `POST /auth/login`."
    ),
    responses={
        401: {"description": "Token ausente, inválido ou expirado"},
    },
)
def me(usuario_atual: Usuario = Depends(get_usuario_atual)):
    return UsuarioResponse(
        id=usuario_atual.id,
        nome=usuario_atual.nome,
        email=usuario_atual.email,
    )


@router.patch(
    "/me",
    response_model=UsuarioResponse,
    summary="Atualiza os dados do usuário autenticado",
    description=(
        "Atualiza nome e/ou email do usuário autenticado. Campos omitidos ou nulos "
        "permanecem inalterados. Requer token JWT válido."
    ),
    responses={
        400: {"description": "Já existe um usuário com este email"},
        401: {"description": "Token ausente, inválido ou expirado"},
    },
)
def atualizar_me(
    request: AtualizarUsuarioRequest,
    usuario_atual: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    try:
        repository = SQLAlchemyUsuarioRepository(db)
        atualizar_usuario = AtualizarUsuario(repository)

        usuario = atualizar_usuario.execute(
            usuario_id=usuario_atual.id,
            nome=request.nome,
            email=request.email,
        )

        return UsuarioResponse(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.patch(
    "/me/senha",
    status_code=204,
    summary="Altera a senha do usuário autenticado",
    description="Exige a senha atual para autorizar a troca. Requer token JWT válido.",
    responses={
        400: {"description": "Senha atual incorreta"},
        401: {"description": "Token ausente, inválido ou expirado"},
    },
)
def alterar_senha(
    request: AlterarSenhaRequest,
    usuario_atual: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    try:
        repository = SQLAlchemyUsuarioRepository(db)
        alterar_senha_use_case = AlterarSenha(repository, BcryptPasswordHasher())

        alterar_senha_use_case.execute(
            usuario_id=usuario_atual.id,
            senha_atual=request.senha_atual,
            senha_nova=request.senha_nova,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.delete(
    "/me",
    status_code=204,
    summary="Exclui a conta do usuário autenticado",
    description="Remove permanentemente o usuário autenticado. Requer token JWT válido.",
    responses={
        401: {"description": "Token ausente, inválido ou expirado"},
    },
)
def excluir_me(
    usuario_atual: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    repository = SQLAlchemyUsuarioRepository(db)
    ExcluirUsuario(repository).execute(usuario_atual.id)
