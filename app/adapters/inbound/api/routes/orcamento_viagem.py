from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.adapters.inbound.api.schemas.orcamento_schema import (
    DefinirOrcamentoRequest,
    ResumoFinanceiroResponse,
)
from app.adapters.inbound.api.security import get_usuario_atual
from app.application.use_cases.gerenciar_orcamento_viagem import GerenciarOrcamentoViagem
from app.domain.entities.usuario import Usuario
from app.infrastructure.dependencies import get_gerenciar_orcamento_viagem

router = APIRouter(prefix="/viagens/{viagem_id}/orcamento", tags=["Orçamento"])
UsuarioAtual = Annotated[Usuario, Depends(get_usuario_atual)]
CasoOrcamento = Annotated[GerenciarOrcamentoViagem, Depends(get_gerenciar_orcamento_viagem)]
IdPositivo = Annotated[int, Path(ge=1)]
_LEITURA = {
    401: {"description": "Token ausente, inválido ou expirado"},
    404: {"description": "Viagem inexistente ou da qual o usuário não participa"},
}


@router.get(
    "",
    response_model=ResumoFinanceiroResponse,
    summary="Consulta o resumo financeiro da viagem",
    description="Criador e colaboradores consultam. Retorna orçamento total, total "
    "planejado nas atividades, saldo e percentuais por categoria, sempre recalculados "
    "a partir das atividades atuais.",
    responses=_LEITURA,
)
def consultar(viagem_id: IdPositivo, usuario: UsuarioAtual, caso: CasoOrcamento):
    return ResumoFinanceiroResponse.model_validate(caso.consultar_resumo(viagem_id, usuario.id))


@router.put(
    "",
    response_model=ResumoFinanceiroResponse,
    summary="Define ou altera o orçamento total da viagem",
    description="Criador/editor. Cada viagem tem um único orçamento, na moeda da "
    "viagem; enviar outro valor o substitui. Retorna o resumo atualizado.",
    responses={
        **_LEITURA,
        422: {"description": "Valor ausente, negativo, não finito ou com mais de duas casas"},
        403: {"description": "Colaborador sem permissão de edição"},
    },
)
def definir(
    viagem_id: IdPositivo,
    request: DefinirOrcamentoRequest,
    usuario: UsuarioAtual,
    caso: CasoOrcamento,
):
    return ResumoFinanceiroResponse.model_validate(
        caso.definir(viagem_id, usuario.id, request.valor_total)
    )
