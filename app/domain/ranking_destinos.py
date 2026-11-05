"""Ranking público de destinos (RF25).

Destinos não são avaliados diretamente (D2): a nota de um destino agrega as avaliações
das atividades do catálogo que pertencem a ele.

Para que um destino com uma única nota 5 não passe à frente de outro com dezenas de
notas altas, a ordenação usa a média bayesiana:

    nota_ranking = (m * C + soma_das_notas) / (m + total_avaliacoes)

em que `C` é a média de todas as avaliações do catálogo e `m` é `RANKING_PESO_PRIORI`.
Desempate estável: nota_ranking exata (decrescente), total de avaliações (decrescente)
e id do destino (crescente). Destinos sem avaliação ficam fora do ranking.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

from app.domain.entities.catalogo import DestinoCatalogo
from app.domain.regras import RANKING_PESO_PRIORI

CENTESIMO = Decimal("0.01")


def _arredondar(valor: Fraction) -> Decimal:
    exato = Decimal(valor.numerator) / Decimal(valor.denominator)
    return exato.quantize(CENTESIMO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, kw_only=True)
class AvaliacoesDestino:
    """Agregado das avaliações das atividades de um destino do catálogo."""

    destino: DestinoCatalogo
    total_avaliacoes: int
    soma_notas: int


@dataclass(frozen=True, kw_only=True)
class DestinoRanqueado:
    posicao: int
    destino: DestinoCatalogo
    media_avaliacoes: Decimal
    nota_ranking: Decimal
    total_avaliacoes: int


@dataclass(frozen=True, kw_only=True)
class RankingDestinos:
    media_geral: Decimal | None
    peso_priori: int
    itens: list[DestinoRanqueado]


def ranquear_destinos(
    agregados: Iterable[AvaliacoesDestino], limite: int, peso_priori: int = RANKING_PESO_PRIORI
) -> RankingDestinos:
    avaliados = [a for a in agregados if a.total_avaliacoes > 0]
    total = sum(a.total_avaliacoes for a in avaliados)
    if not total:
        return RankingDestinos(media_geral=None, peso_priori=peso_priori, itens=[])
    media_geral = Fraction(sum(a.soma_notas for a in avaliados), total)

    def nota(a: AvaliacoesDestino) -> Fraction:
        return (peso_priori * media_geral + a.soma_notas) / (peso_priori + a.total_avaliacoes)

    ordenados = sorted(avaliados, key=lambda a: (-nota(a), -a.total_avaliacoes, a.destino.id))
    return RankingDestinos(
        media_geral=_arredondar(media_geral),
        peso_priori=peso_priori,
        itens=[
            DestinoRanqueado(
                posicao=posicao,
                destino=a.destino,
                media_avaliacoes=_arredondar(Fraction(a.soma_notas, a.total_avaliacoes)),
                nota_ranking=_arredondar(nota(a)),
                total_avaliacoes=a.total_avaliacoes,
            )
            for posicao, a in enumerate(ordenados[:limite], start=1)
        ],
    )
