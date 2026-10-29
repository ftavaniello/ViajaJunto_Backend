from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials

from app.adapters.inbound.api.schemas.auth_schema import LoginRequest, TokenResponse
from app.adapters.inbound.api.security import bearer_scheme, get_usuario_atual
from app.application.use_cases.autenticar_usuario import AutenticarUsuario
from app.application.use_cases.encerrar_sessao import EncerrarSessao
from app.domain.entities.usuario import Usuario
from app.infrastructure.dependencies import (
    get_autenticar_usuario,
    get_encerrar_sessao,
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


@router.post(
    "/logout",
    status_code=204,
    summary="Encerra a sessão do token enviado",
    description=(
        "Revoga no servidor o token enviado em `Authorization: Bearer <access_token>`. "
        "A partir daí ele, e qualquer cópia dele, recebe 401 em todos os endpoints "
        "protegidos, mesmo antes de expirar. Outras sessões do mesmo usuário (outros "
        "logins) continuam válidas. Um segundo logout com o mesmo token retorna 401."
    ),
    responses={
        401: {"description": "Token ausente, inválido, expirado ou já encerrado"},
    },
)
def logout(
    usuario_atual: Usuario = Depends(get_usuario_atual),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    caso: EncerrarSessao = Depends(get_encerrar_sessao),
):
    # get_usuario_atual ja recusou requisicoes sem token ou com token invalido.
    caso.execute(credentials.credentials)
