from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.adapters.inbound.api.schemas.catalogo_schema import DadosAtividadeCatalogoResponse
from app.domain.enums import StatusAtividade

StatusAtividadeEntrada = Literal[
    StatusAtividade.PENDENTE,
    StatusAtividade.CONFIRMADA,
    StatusAtividade.CONCLUIDA,
]
CustoAtividade = Annotated[
    Decimal, Field(ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
]
DuracaoAtividade = Annotated[int, Field(ge=1, le=2147483647, strict=True)]


class CriarAtividadeViagemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    catalogo_atividade_id: int = Field(ge=1, strict=True)
    data: date
    hora_inicio: time | None = Field(default=None, description="Horário local, sem fuso.")
    duracao_minutos: DuracaoAtividade | None = None
    custo_previsto: CustoAtividade = Decimal("0.00")
    status: StatusAtividadeEntrada = StatusAtividade.PENDENTE


class AtualizarAtividadeViagemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data: date | None = Field(default=None, description="Nulo/omitido preserva a data.")
    hora_inicio: time | None = Field(default=None, description="Nulo remove; omitido preserva.")
    duracao_minutos: DuracaoAtividade | None = Field(
        default=None,
        description="Nulo remove; omitido preserva.",
    )
    custo_previsto: CustoAtividade | None = Field(
        default=None, description="Nulo/omitido preserva."
    )
    status: StatusAtividadeEntrada | None = Field(
        default=None, description="Nulo/omitido preserva."
    )


class AtividadeViagemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    viagem_id: int
    destino_viagem_id: int
    catalogo_atividade_id: int
    atividade: DadosAtividadeCatalogoResponse
    data: date
    hora_inicio: time | None
    duracao_minutos: int | None
    custo_previsto: Decimal = Field(description="Valor decimal na moeda da viagem, com duas casas.")
    status: StatusAtividade = Field(description="Cancelada pode aparecer somente em dados legados.")
    realizada_em: datetime | None
    realizada_por_id: int | None
