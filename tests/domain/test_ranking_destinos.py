from decimal import Decimal

from app.domain.entities.catalogo import DestinoCatalogo
from app.domain.ranking_destinos import AvaliacoesDestino, ranquear_destinos


def agregado(destino_id, total, soma):
    return AvaliacoesDestino(
        destino=DestinoCatalogo(id=destino_id, nome=f"D{destino_id}", pais_codigo="BR"),
        total_avaliacoes=total,
        soma_notas=soma,
    )


def ordem(ranking):
    return [item.destino.id for item in ranking.itens]


def test_sem_avaliacoes_ranking_vazio():
    ranking = ranquear_destinos([], limite=10)

    assert ranking.itens == []
    assert ranking.media_geral is None


def test_destino_sem_avaliacao_fica_fora():
    ranking = ranquear_destinos([agregado(1, 0, 0), agregado(2, 1, 4)], limite=10)

    assert ordem(ranking) == [2]


def test_media_bayesiana_favorece_muitas_notas_altas_sobre_uma_unica_nota_5():
    # C = (5 + 95 + 20) / (1 + 20 + 10) = 3,87...; m = 5.
    ranking = ranquear_destinos(
        [agregado(1, 1, 5), agregado(2, 20, 95), agregado(3, 10, 20)], limite=10
    )

    assert ordem(ranking) == [2, 1, 3]
    primeiro, segundo, terceiro = ranking.itens
    assert (primeiro.posicao, primeiro.media_avaliacoes, primeiro.total_avaliacoes) == (
        1, Decimal("4.75"), 20,
    )
    assert primeiro.nota_ranking == Decimal("4.57")  # (5*120/31 + 95) / 25 = 4,574...
    assert (segundo.media_avaliacoes, segundo.nota_ranking) == (Decimal("5.00"), Decimal("4.06"))
    assert terceiro.nota_ranking == Decimal("2.62")  # (5*120/31 + 20) / 15 = 2,623...
    assert ranking.media_geral == Decimal("3.87")


def test_nota_ranking_puxa_para_a_media_geral():
    ranking = ranquear_destinos([agregado(1, 1, 1), agregado(2, 1, 5)], limite=10)

    # C = 3; (5*3 + 5) / 6 = 3,33 e (5*3 + 1) / 6 = 2,67.
    assert [str(i.nota_ranking) for i in ranking.itens] == ["3.33", "2.67"]


def test_desempate_por_total_de_avaliacoes_e_depois_por_id():
    ranking = ranquear_destinos(
        [agregado(3, 2, 8), agregado(2, 4, 16), agregado(1, 2, 8)], limite=10
    )

    # Todos com média 4 = C, logo mesma nota de ranking.
    assert ordem(ranking) == [2, 1, 3]
    assert [i.posicao for i in ranking.itens] == [1, 2, 3]


def test_ordem_nao_depende_da_ordem_de_entrada():
    dados = [agregado(i, i, i * (i % 5 + 1)) for i in range(1, 9)]

    assert ordem(ranquear_destinos(dados, 10)) == ordem(ranquear_destinos(dados[::-1], 10))


def test_limite_corta_depois_de_ordenar_e_media_geral_considera_todos():
    ranking = ranquear_destinos([agregado(1, 1, 1), agregado(2, 1, 5), agregado(3, 1, 3)], 1)

    assert ordem(ranking) == [2]
    assert ranking.media_geral == Decimal("3.00")
