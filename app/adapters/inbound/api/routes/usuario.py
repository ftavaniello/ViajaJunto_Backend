from fastapi import APIRouter, Depends, Response

from app.adapters.inbound.api.schemas.usuario_schema import (
    AlterarSenhaRequest,
    AtualizarUsuarioRequest,
    CriarUsuarioRequest,
    ResumoUsuariosResponse,
    UsuarioResponse,
)
from app.adapters.inbound.api.security import get_usuario_atual
from app.application.use_cases.alterar_senha import AlterarSenha
from app.application.use_cases.atualizar_usuario import AtualizarUsuario
from app.application.use_cases.consultar_resumo_usuarios import ConsultarResumoUsuarios
from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.excluir_usuario import ExcluirUsuario
from app.domain.entities.usuario import Usuario
from app.infrastructure.dependencies import (
    get_alterar_senha,
    get_atualizar_usuario,
    get_consultar_resumo,
    get_criar_usuario,
    get_excluir_usuario,
)

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
def criar(
    request: CriarUsuarioRequest,
    caso: CriarUsuario = Depends(get_criar_usuario),
):
    usuario = caso.execute(nome=request.nome, email=request.email, senha=request.senha)
    return UsuarioResponse(id=usuario.id, nome=usuario.nome, email=usuario.email)


@router.get(
    "/resumo",
    response_model=ResumoUsuariosResponse,
    summary="Consulta o total de usuarios cadastrados",
    description=(
        "Requer JWT. Cacheia somente a contagem; a autenticacao continua consultando o banco. "
        "X-Cache indica HIT (Redis), MISS (banco e cache preenchido) ou BYPASS (sem cache)."
    ),
    responses={
        200: {"description": "Total de usuarios", "headers": {
            "X-Cache": {"description": "Origem da contagem",
                        "schema": {"type": "string", "enum": ["HIT", "MISS", "BYPASS"]}},
        }},
        401: {"description": "Token ausente, invalido, expirado ou conta excluida"},
    },
)
def resumo(
    response: Response,
    usuario_atual: Usuario = Depends(get_usuario_atual),
    caso: ConsultarResumoUsuarios = Depends(get_consultar_resumo),
):
    total, origem = caso.execute()
    response.headers["X-Cache"] = origem.value
    response.headers["Cache-Control"] = "no-store"
    return ResumoUsuariosResponse(total_usuarios=total)


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
    caso: AtualizarUsuario = Depends(get_atualizar_usuario),
):
    usuario = caso.execute(usuario_id=usuario_atual.id, nome=request.nome, email=request.email)
    return UsuarioResponse(id=usuario.id, nome=usuario.nome, email=usuario.email)


@router.patch(
    "/me/senha",
    status_code=204,
    summary="Altera a senha do usuário autenticado",
    description=(
        "Exige a senha atual para autorizar a troca. Requer token JWT válido. "
        "A troca encerra todas as sessões do usuário, inclusive a usada nesta "
        "requisição: os tokens emitidos antes passam a receber 401 e é preciso "
        "fazer login novamente com a nova senha."
    ),
    responses={
        400: {"description": "Senha atual incorreta"},
        401: {"description": "Token ausente, inválido ou expirado"},
    },
)
def alterar_senha(
    request: AlterarSenhaRequest,
    usuario_atual: Usuario = Depends(get_usuario_atual),
    caso: AlterarSenha = Depends(get_alterar_senha),
):
    caso.execute(
        usuario_id=usuario_atual.id, senha_atual=request.senha_atual, senha_nova=request.senha_nova,
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
    caso: ExcluirUsuario = Depends(get_excluir_usuario),
):
    caso.execute(usuario_atual.id)
