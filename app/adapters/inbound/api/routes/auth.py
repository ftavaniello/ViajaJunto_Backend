from fastapi import APIRouter, Depends

from app.adapters.inbound.api.schemas.auth_schema import LoginRequest, TokenResponse
from app.application.use_cases.autenticar_usuario import AutenticarUsuario
from app.infrastructure.dependencies import (
    get_autenticar_usuario,
)

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
def login(
    request: LoginRequest,
    caso: AutenticarUsuario = Depends(get_autenticar_usuario),
):
    return TokenResponse(access_token=caso.execute(email=request.email, senha=request.senha))
