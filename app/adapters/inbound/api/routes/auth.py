from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.adapters.inbound.api.schemas.auth_schema import LoginRequest, TokenResponse
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.adapters.outbound.security.pyjwt_token_service import PyJWTTokenService
from app.application.use_cases.autenticar_usuario import AutenticarUsuario
from app.infrastructure.database import get_db

router = APIRouter(
    prefix="/auth",
    tags=["Autenticação"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autentica um usuário e retorna um token JWT",
    description=(
        "Valida o email e a senha informados e retorna um access token (JWT). "
        "Envie esse token no header `Authorization: Bearer <access_token>` para "
        "acessar os endpoints protegidos, como `GET /usuarios/me`."
    ),
    responses={
        401: {"description": "Email ou senha inválidos"},
    },
)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    try:
        repository = SQLAlchemyUsuarioRepository(db)
        autenticar_usuario = AutenticarUsuario(
            repository=repository,
            password_hasher=BcryptPasswordHasher(),
            token_service=PyJWTTokenService(),
        )

        token = autenticar_usuario.execute(email=request.email, senha=request.senha)

        return TokenResponse(access_token=token)

    except ValueError as error:
        raise HTTPException(
            status_code=401,
            detail=str(error),
        )
