from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.adapters.inbound.api.schemas.atividade_viagem_schema import (
    AtividadeViagemResponse,
    AtualizarAtividadeViagemRequest,
    CriarAtividadeViagemRequest,
)
from app.adapters.inbound.api.security import get_usuario_atual
from app.application.use_cases.gerenciar_atividades_viagem import GerenciarAtividadesViagem
from app.domain.entities.usuario import Usuario
from app.infrastructure.dependencies import get_gerenciar_atividades_viagem

router = APIRouter(
    prefix="/viagens/{viagem_id}/destinos/{destino_id}/atividades", tags=["Atividades do roteiro"]
)
UsuarioAtual = Annotated[Usuario, Depends(get_usuario_atual)]
CasoAtividades = Annotated[GerenciarAtividadesViagem, Depends(get_gerenciar_atividades_viagem)]
IdPositivo = Annotated[int, Path(ge=1)]
_LEITURA = {
    401: {"description": "Token ausente, inválido ou expirado"},
    404: {"description": "Viagem, parada ou atividade inexistente ou fora deste contexto"},
}
_EDICAO = {
    **_LEITURA,
    403: {"description": "Colaborador sem permissão de edição"},
    400: {"description": "Data, horário, custo, duração ou vínculo de catálogo inválido"},
}


@router.get(
    "",
    response_model=list[AtividadeViagemResponse],
    summary="Lista atividades por ordem cronológica",
    description="Criador e colaboradores consultam. Ordem: data, horário e id. "
    "Sem horário fica ao fim do respectivo dia.",
    responses=_LEITURA,
)
def listar(
    viagem_id: IdPositivo, destino_id: IdPositivo, usuario: UsuarioAtual, caso: CasoAtividades
):
    return [
        AtividadeViagemResponse.model_validate(a)
        for a in caso.listar(viagem_id, destino_id, usuario.id)
    ]


@router.post(
    "",
    response_model=AtividadeViagemResponse,
    status_code=201,
    summary="Adiciona atividade do catálogo à parada",
    description="Criador/editor. A atividade deve pertencer ao destino da parada. "
    "O custo é expresso na moeda da viagem. Não altera o catálogo.",
    responses=_EDICAO,
)
def criar(
    viagem_id: IdPositivo,
    destino_id: IdPositivo,
    request: CriarAtividadeViagemRequest,
    usuario: UsuarioAtual,
    caso: CasoAtividades,
):
    return AtividadeViagemResponse.model_validate(
        caso.criar(
            viagem_id,
            destino_id,
            usuario.id,
            **request.model_dump(),
        )
    )


@router.get(
    "/{atividade_id}",
    response_model=AtividadeViagemResponse,
    summary="Consulta uma atividade do roteiro",
    description="Exige participação na viagem e vínculo com a parada informada.",
    responses=_LEITURA,
)
def consultar(
    viagem_id: IdPositivo,
    destino_id: IdPositivo,
    atividade_id: IdPositivo,
    usuario: UsuarioAtual,
    caso: CasoAtividades,
):
    return AtividadeViagemResponse.model_validate(
        caso.consultar(viagem_id, destino_id, atividade_id, usuario.id)
    )


@router.patch(
    "/{atividade_id}",
    response_model=AtividadeViagemResponse,
    summary="Atualiza data, horário, duração, custo ou status",
    description="Criador/editor. Horário e duração nulos são removidos; omitidos são "
    "preservados. Demais campos nulos/omitidos permanecem inalterados. "
    "Ao concluir, o servidor registra quem concluiu e quando.",
    responses=_EDICAO,
)
def atualizar(
    viagem_id: IdPositivo,
    destino_id: IdPositivo,
    atividade_id: IdPositivo,
    request: AtualizarAtividadeViagemRequest,
    usuario: UsuarioAtual,
    caso: CasoAtividades,
):
    return AtividadeViagemResponse.model_validate(
        caso.atualizar(
            viagem_id,
            destino_id,
            atividade_id,
            usuario.id,
            **request.model_dump(),
            limpar_hora="hora_inicio" in request.model_fields_set and request.hora_inicio is None,
            limpar_duracao="duracao_minutos" in request.model_fields_set
            and request.duracao_minutos is None,
        )
    )


@router.delete(
    "/{atividade_id}",
    status_code=204,
    summary="Remove atividade do roteiro",
    description="Criador/editor. Preserva catálogo e avaliações públicas; "
    "remove somente o planejamento desta ocorrência.",
    responses=_EDICAO,
)
def remover(
    viagem_id: IdPositivo,
    destino_id: IdPositivo,
    atividade_id: IdPositivo,
    usuario: UsuarioAtual,
    caso: CasoAtividades,
):
    caso.remover(viagem_id, destino_id, atividade_id, usuario.id)
