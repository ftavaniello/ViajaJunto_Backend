from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import CategoriaAtividade

ValorOrcamento = Annotated[
    Decimal, Field(ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
]
_PERCENTUAL = (
    "Percentual com duas casas (meio para cima); nulo quando o denominador é ausente ou 0."
)


class DefinirOrcamentoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valor_total: ValorOrcamento = Field(
        description="Orçamento total na moeda da viagem. Prefira string, como \"1000.00\"."
    )


class ResumoCategoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    categoria: CategoriaAtividade
    total_planejado: Decimal
    percentual_orcamento: Decimal | None = Field(
        description=f"Custo da categoria / orçamento total × 100. {_PERCENTUAL}"
    )
    percentual_planejado: Decimal | None = Field(
        description=f"Custo da categoria / total planejado × 100. {_PERCENTUAL}"
    )


class ResumoFinanceiroResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    viagem_id: int
    orcamento_total: Decimal | None = Field(description="Nulo enquanto não for definido.")
    total_planejado: Decimal = Field(
        description="Soma dos custos previstos das atividades, exceto canceladas (legado)."
    )
    saldo_disponivel: Decimal | None = Field(
        description="Orçamento total - total planejado; negativo quando estoura. "
        "Nulo sem orçamento definido."
    )
    percentual_consumido: Decimal | None = Field(
        description=f"Total planejado / orçamento total × 100. {_PERCENTUAL}"
    )
    orcamento_excedido: bool
    categorias: list[ResumoCategoriaResponse] = Field(
        description="Todas as categorias de atividade, inclusive as sem custo."
    )
