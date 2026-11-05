from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.adapters.inbound.api.schemas.destino_viagem_schema import (
    AtualizarDestinoViagemRequest,
    CriarDestinoViagemRequest,
    DestinoViagemResponse,
    ReordenarDestinosRequest,
)
from app.adapters.inbound.api.security import get_usuario_atual
from app.application.use_cases.gerenciar_destinos_viagem import GerenciarDestinosViagem
from app.domain.entities.usuario import Usuario
from app.infrastructure.dependencies import get_gerenciar_destinos_viagem

router = APIRouter(prefix="/viagens/{viagem_id}/destinos", tags=["Roteiro"])
UsuarioAtual = Annotated[Usuario, Depends(get_usuario_atual)]
CasoRoteiro = Annotated[GerenciarDestinosViagem, Depends(get_gerenciar_destinos_viagem)]
IdPositivo = Annotated[int, Path(ge=1)]
_LEITURA = {
    401: {"description": "Token ausente, inválido ou expirado"},
    404: {"description": "Viagem/destino inexistente ou sem vínculo com esta viagem"},
}
_EDICAO = {
    **_LEITURA,
    403: {"description": "Colaborador sem permissão de edição"},
    400: {"description": "Datas ou ordem inválidas"},
}


@router.get(
    "",
    response_model=list[DestinoViagemResponse],
    summary="Lista os destinos do roteiro",
    description="Criador e colaboradores consultam por ordem de visita.",
    responses=_LEITURA,
)
def listar(viagem_id: IdPositivo, usuario: UsuarioAtual, caso: CasoRoteiro):
    return [DestinoViagemResponse.model_validate(d) for d in caso.listar(viagem_id, usuario.id)]


@router.post(
    "",
    response_model=DestinoViagemResponse,
    status_code=201,
    summary="Adiciona um destino do catálogo ao roteiro",
    description="Criador/editor. Datas dentro da viagem; permite revisitar o mesmo destino.",
    responses=_EDICAO,
)
def criar(
    viagem_id: IdPositivo,
    request: CriarDestinoViagemRequest,
    usuario: UsuarioAtual,
    caso: CasoRoteiro,
):
    return DestinoViagemResponse.model_validate(
        caso.criar(
            viagem_id,
            usuario.id,
            **request.model_dump(),
        )
    )


@router.put(
    "/ordem",
    response_model=list[DestinoViagemResponse],
    summary="Reordena todos os destinos da viagem",
    description="Criador/editor. Lista completa sem IDs duplicados, ausentes ou alheios.",
    responses=_EDICAO,
)
def reordenar(
    viagem_id: IdPositivo,
    request: ReordenarDestinosRequest,
    usuario: UsuarioAtual,
    caso: CasoRoteiro,
):
    return [
        DestinoViagemResponse.model_validate(d)
        for d in caso.reordenar(viagem_id, usuario.id, request.destinos_ids)
    ]


@router.get(
    "/{destino_id}",
    response_model=DestinoViagemResponse,
    summary="Consulta um destino da viagem",
    description="Criador e colaboradores consultam a parada exclusivamente dentro desta viagem.",
    responses=_LEITURA,
)
def consultar(
    viagem_id: IdPositivo, destino_id: IdPositivo, usuario: UsuarioAtual, caso: CasoRoteiro
):
    return DestinoViagemResponse.model_validate(caso.consultar(viagem_id, destino_id, usuario.id))


@router.patch(
    "/{destino_id}",
    response_model=DestinoViagemResponse,
    summary="Atualiza a estadia e descrição particular do destino",
    description="Criador/editor. Nulo/omitido preserva; texto vazio limpa o campo. "
    "Não altera o catálogo; preserva o período das atividades existentes.",
    responses=_EDICAO,
)
def atualizar(
    viagem_id: IdPositivo,
    destino_id: IdPositivo,
    request: AtualizarDestinoViagemRequest,
    usuario: UsuarioAtual,
    caso: CasoRoteiro,
):
    return DestinoViagemResponse.model_validate(
        caso.atualizar(
            viagem_id,
            destino_id,
            usuario.id,
            **request.model_dump(),
        )
    )


@router.delete(
    "/{destino_id}",
    status_code=204,
    summary="Remove uma parada e suas atividades",
    description="Criador/editor. Exclui atividades vinculadas e compacta a ordem; "
    "preserva o catálogo e avaliações públicas.",
    responses=_EDICAO,
)
def remover(
    viagem_id: IdPositivo, destino_id: IdPositivo, usuario: UsuarioAtual, caso: CasoRoteiro
):
    caso.remover(viagem_id, destino_id, usuario.id)
