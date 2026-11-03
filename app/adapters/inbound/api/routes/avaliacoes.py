from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.adapters.inbound.api.schemas.avaliacao_schema import AvaliarAtividadeRequest
from app.adapters.inbound.api.schemas.catalogo_schema import ReviewCatalogoResponse
from app.adapters.inbound.api.security import get_usuario_atual
from app.application.use_cases.avaliar_atividade_viagem import AvaliarAtividadeViagem
from app.domain.entities.usuario import Usuario
from app.infrastructure.dependencies import get_avaliar_atividade_viagem

router = APIRouter(tags=["Avaliações"])
IdPositivo = Annotated[int, Path(ge=1)]


@router.put(
    "/viagens/{viagem_id}/destinos/{destino_id}/atividades/{atividade_id}/avaliacao",
    response_model=ReviewCatalogoResponse,
    summary="Publica ou atualiza minha avaliação de uma atividade concluída",
    description=(
        "Criador, editor e visualizador participantes podem avaliar. Exige conclusão "
        "registrada na ocorrência indicada. Uma avaliação por usuário e atividade do "
        "catálogo: reenviar atualiza nota/comentário, preservando ID e data de criação. "
        "O comentário omitido ou nulo remove o comentário anterior. A avaliação torna-se pública."
    ),
    responses={
        400: {"description": "Nota ou comentário inválidos"},
        401: {"description": "Token ausente, inválido ou expirado"},
        403: {"description": "Atividade ainda não concluída"},
        404: {"description": "Viagem ou atividade inexistente ou fora do contexto autorizado"},
    },
)
def avaliar(
    viagem_id: IdPositivo,
    destino_id: IdPositivo,
    atividade_id: IdPositivo,
    request: AvaliarAtividadeRequest,
    usuario: Annotated[Usuario, Depends(get_usuario_atual)],
    caso: Annotated[AvaliarAtividadeViagem, Depends(get_avaliar_atividade_viagem)],
):
    return ReviewCatalogoResponse.model_validate(
        caso.execute(
            viagem_id,
            destino_id,
            atividade_id,
            usuario.id,
            request.nota,
            request.comentario,
        )
    )
