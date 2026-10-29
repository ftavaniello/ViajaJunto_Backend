from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials

from app.adapters.inbound.api.schemas.auth_schema import (
    LoginRequest,
    MensagemResponse,
    RedefinirSenhaRequest,
    SolicitarRecuperacaoSenhaRequest,
    TokenResponse,
)
from app.adapters.inbound.api.security import bearer_scheme, get_usuario_atual
from app.application.use_cases.autenticar_usuario import AutenticarUsuario
from app.application.use_cases.encerrar_sessao import EncerrarSessao
from app.application.use_cases.redefinir_senha import RedefinirSenha
from app.application.use_cases.solicitar_recuperacao_senha import SolicitarRecuperacaoSenha
from app.domain.entities.usuario import Usuario
from app.infrastructure.dependencies import (
    get_autenticar_usuario,
    get_encerrar_sessao,
    get_redefinir_senha,
    get_solicitar_recuperacao_senha,
)

MENSAGEM_RECUPERACAO = (
    "Se o email estiver cadastrado, enviaremos um link para redefinir a senha."
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


@router.post(
    "/recuperar-senha",
    status_code=202,
    response_model=MensagemResponse,
    summary="Solicita a recuperação de senha por email",
    description=(
        "Endpoint público. Se o email pertencer a uma conta, envia para ele um link "
        "de redefinição de senha, válido por 60 minutos e de uso único; pedir de novo "
        "invalida o link anterior. A resposta é sempre a mesma (`202`), exista ou não "
        "a conta e mesmo se o envio do email falhar, para não revelar quais emails "
        "estão cadastrados."
    ),
)
def recuperar_senha(
    request: SolicitarRecuperacaoSenhaRequest,
    caso: SolicitarRecuperacaoSenha = Depends(get_solicitar_recuperacao_senha),
):
    caso.execute(email=request.email)
    return MensagemResponse(detail=MENSAGEM_RECUPERACAO)


@router.post(
    "/redefinir-senha",
    status_code=204,
    summary="Define uma nova senha com o token recebido por email",
    description=(
        "Endpoint público. Troca a senha usando o `token` do link de recuperação. "
        "O token deixa de valer após o uso, e todas as sessões abertas do usuário "
        "são encerradas, como na troca de senha: é preciso fazer login com a nova senha."
    ),
    responses={
        400: {"description": "Token inválido, expirado ou já utilizado, ou senha nova inválida"},
    },
)
def redefinir_senha(
    request: RedefinirSenhaRequest,
    caso: RedefinirSenha = Depends(get_redefinir_senha),
):
    caso.execute(token=request.token, senha_nova=request.senha_nova)
