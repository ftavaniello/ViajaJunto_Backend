from fastapi import APIRouter, Depends

from app.adapters.inbound.api.schemas.viagem_schema import (
    AtualizarViagemRequest,
    CriarViagemRequest,
    ViagemResponse,
)
from app.adapters.inbound.api.security import get_usuario_atual
from app.application.use_cases.atualizar_viagem import AtualizarViagem
from app.application.use_cases.consultar_viagem import ConsultarViagem
from app.application.use_cases.criar_viagem import CriarViagem
from app.application.use_cases.excluir_viagem import ExcluirViagem
from app.application.use_cases.listar_viagens import ListarViagens
from app.domain.entities.usuario import Usuario
from app.domain.entities.viagem import Viagem
from app.infrastructure.dependencies import (
    get_atualizar_viagem,
    get_consultar_viagem,
    get_criar_viagem,
    get_excluir_viagem,
    get_listar_viagens,
)

router = APIRouter(
    prefix="/viagens",
    tags=["Viagens"],
)

_NAO_AUTENTICADO = {401: {"description": "Token ausente, inválido ou expirado"}}
_NAO_ENCONTRADA = {
    404: {"description": "Viagem inexistente ou da qual o usuário não participa"},
}


def _to_response(viagem: Viagem) -> ViagemResponse:
    return ViagemResponse(
        id=viagem.id,
        criador_id=viagem.criador_id,
        nome=viagem.nome,
        descricao=viagem.descricao,
        data_inicio=viagem.data_inicio,
        data_fim=viagem.data_fim,
        status=viagem.status,
        criado_em=viagem.criado_em,
        atualizado_em=viagem.atualizado_em,
    )


@router.post(
    "",
    response_model=ViagemResponse,
    status_code=201,
    summary="Cria uma viagem",
    description=(
        "Cria uma viagem com status `planejando`. O criador é o usuário do token; "
        "não é aceito no corpo da requisição."
    ),
    responses={
        400: {"description": "Nome vazio ou data de fim anterior à de início"},
        **_NAO_AUTENTICADO,
    },
)
def criar(
    request: CriarViagemRequest,
    usuario_atual: Usuario = Depends(get_usuario_atual),
    caso: CriarViagem = Depends(get_criar_viagem),
):
    viagem = caso.execute(
        criador_id=usuario_atual.id,
        nome=request.nome,
        descricao=request.descricao,
        data_inicio=request.data_inicio,
        data_fim=request.data_fim,
    )
    return _to_response(viagem)


@router.get(
    "",
    response_model=list[ViagemResponse],
    summary="Lista as viagens do usuário autenticado",
    description="Viagens criadas pelo usuário ou das quais ele é colaborador.",
    responses=_NAO_AUTENTICADO,
)
def listar(
    usuario_atual: Usuario = Depends(get_usuario_atual),
    caso: ListarViagens = Depends(get_listar_viagens),
):
    return [_to_response(viagem) for viagem in caso.execute(usuario_atual.id)]


@router.get(
    "/{viagem_id}",
    response_model=ViagemResponse,
    summary="Consulta uma viagem",
    description="Permitido ao criador e aos colaboradores da viagem.",
    responses={**_NAO_AUTENTICADO, **_NAO_ENCONTRADA},
)
def consultar(
    viagem_id: int,
    usuario_atual: Usuario = Depends(get_usuario_atual),
    caso: ConsultarViagem = Depends(get_consultar_viagem),
):
    return _to_response(caso.execute(viagem_id=viagem_id, usuario_id=usuario_atual.id))


@router.patch(
    "/{viagem_id}",
    response_model=ViagemResponse,
    summary="Atualiza dados gerais e status da viagem",
    description=(
        "Permitido ao criador e a colaboradores editores. Campos omitidos ou nulos "
        "permanecem inalterados; o período resultante é validado."
    ),
    responses={
        400: {"description": "Nome vazio ou data de fim anterior à de início"},
        **_NAO_AUTENTICADO,
        403: {"description": "Colaborador sem permissão de edição"},
        **_NAO_ENCONTRADA,
    },
)
def atualizar(
    viagem_id: int,
    request: AtualizarViagemRequest,
    usuario_atual: Usuario = Depends(get_usuario_atual),
    caso: AtualizarViagem = Depends(get_atualizar_viagem),
):
    viagem = caso.execute(
        viagem_id=viagem_id,
        usuario_id=usuario_atual.id,
        nome=request.nome,
        descricao=request.descricao,
        data_inicio=request.data_inicio,
        data_fim=request.data_fim,
        status=request.status,
    )
    return _to_response(viagem)


@router.delete(
    "/{viagem_id}",
    status_code=204,
    summary="Exclui a viagem",
    description="Somente o criador. Remove também colaboradores, roteiro e orçamento da viagem.",
    responses={
        **_NAO_AUTENTICADO,
        403: {"description": "Somente o criador pode excluir a viagem"},
        **_NAO_ENCONTRADA,
    },
)
def excluir(
    viagem_id: int,
    usuario_atual: Usuario = Depends(get_usuario_atual),
    caso: ExcluirViagem = Depends(get_excluir_viagem),
):
    caso.execute(viagem_id=viagem_id, usuario_id=usuario_atual.id)
