"""Orçamento da viagem (RF15) e resumo financeiro (RF17).

Fórmula acordada para o resumo:

- total planejado = soma dos custos previstos das atividades da viagem, exceto as
  canceladas (status legado);
- saldo disponível = orçamento total - total planejado (negativo quando estoura);
- percentual por categoria sobre o orçamento = custo da categoria / orçamento total;
- participação da categoria no planejado = custo da categoria / total planejado.

Percentuais vão de 0 a 100 (podem passar de 100 quando o orçamento estoura), com duas
casas e arredondamento meio-para-cima, calculados a partir dos valores exatos.
Quando o denominador é ausente ou zero, o percentual é nulo (não há divisão por zero).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import CategoriaAtividade
from app.domain.errors import DadosInvalidos

CENTAVO = Decimal("0.01")
VALOR_MAXIMO = Decimal("9999999999.99")  # NUMERIC(12,2)


def _percentual(parte: Decimal, todo: Decimal | None) -> Decimal | None:
    if not todo:
        return None
    return (parte * 100 / todo).quantize(CENTAVO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, kw_only=True)
class Orcamento:
    viagem_id: int
    valor_total: Decimal

    def __post_init__(self):
        valor = self.valor_total
        if (
            not isinstance(valor, Decimal)
            or not valor.is_finite()
            or not Decimal("0") <= valor <= VALOR_MAXIMO
        ):
            raise DadosInvalidos(
                "Orçamento deve ser um Decimal finito, não negativo e de até 12 dígitos"
            )
        if valor != valor.quantize(CENTAVO):
            raise DadosInvalidos("Orçamento deve ter no máximo duas casas decimais")
        object.__setattr__(self, "valor_total", valor.quantize(CENTAVO))


@dataclass(frozen=True, kw_only=True)
class ResumoCategoria:
    categoria: CategoriaAtividade
    total_planejado: Decimal
    percentual_orcamento: Decimal | None
    percentual_planejado: Decimal | None


@dataclass(frozen=True, kw_only=True)
class ResumoFinanceiro:
    viagem_id: int
    orcamento_total: Decimal | None
    total_planejado: Decimal
    saldo_disponivel: Decimal | None
    percentual_consumido: Decimal | None
    orcamento_excedido: bool
    categorias: list[ResumoCategoria]

    @classmethod
    def calcular(
        cls,
        viagem_id: int,
        orcamento: Orcamento | None,
        custos_por_categoria: Mapping[CategoriaAtividade, Decimal],
    ) -> "ResumoFinanceiro":
        """Monta o resumo; todas as categorias aparecem, na ordem do enum, mesmo zeradas."""
        custos = {
            categoria: Decimal(custos_por_categoria.get(categoria, 0)).quantize(CENTAVO)
            for categoria in CategoriaAtividade
        }
        total = sum(custos.values(), Decimal("0.00"))
        limite = orcamento.valor_total if orcamento else None
        return cls(
            viagem_id=viagem_id,
            orcamento_total=limite,
            total_planejado=total,
            saldo_disponivel=None if limite is None else limite - total,
            percentual_consumido=_percentual(total, limite),
            orcamento_excedido=limite is not None and total > limite,
            categorias=[
                ResumoCategoria(
                    categoria=categoria,
                    total_planejado=valor,
                    percentual_orcamento=_percentual(valor, limite),
                    percentual_planejado=_percentual(valor, total),
                )
                for categoria, valor in custos.items()
            ],
        )
