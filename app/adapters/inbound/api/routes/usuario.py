from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.adapters.inbound.api.schemas.usuario_schema import (
    CriarUsuarioRequest,
    UsuarioResponse,
)
from app.adapters.inbound.api.security import get_usuario_atual
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.application.use_cases.criar_usuario import CriarUsuario
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
