from datetime import date

import pytest

from app.domain.enums import StatusViagem
from app.domain.paises_visitados import PaisVisitado, ParadaDoParticipante, paises_visitados

HOJE = date(2026, 11, 3)


def parada(pais="PT", chegada=date(2026, 1, 10), status=StatusViagem.CONCLUIDA, viagem_id=1):
    return ParadaDoParticipante(
        viagem_id=viagem_id, status_viagem=status, pais_codigo=pais, data_chegada=chegada
    )


@pytest.mark.parametrize(
    ("status", "chegada", "visitada"),
    [
        (StatusViagem.CONCLUIDA, date(2026, 1, 10), True),
        (StatusViagem.CONFIRMADA, date(2026, 1, 10), True),
        (StatusViagem.PLANEJANDO, date(2026, 1, 10), False),
        (StatusViagem.CONFIRMADA, HOJE, True),  # chegada hoje já conta
        (StatusViagem.CONFIRMADA, date(2026, 11, 4), False),  # viagem futura
        (StatusViagem.CONCLUIDA, date(2027, 1, 1), False),  # concluída por engano no futuro
    ],
)
def test_criterio_de_visita_efetiva(status, chegada, visitada):
    assert parada(status=status, chegada=chegada).visitada(HOJE) is visitada


def test_pais_repetido_aparece_uma_vez_com_periodo_e_viagens_distintas():
    resultado = paises_visitados(
        [
            parada("PT", date(2025, 5, 1), viagem_id=1),
            parada("PT", date(2025, 5, 3), viagem_id=1),
            parada("PT", date(2026, 2, 1), viagem_id=2),
            parada("BR", date(2024, 12, 25), viagem_id=3),
        ],
        HOJE,
    )

    assert resultado == [
        PaisVisitado(
            pais_codigo="BR",
            primeira_visita=date(2024, 12, 25),
            ultima_visita=date(2024, 12, 25),
            total_viagens=1,
        ),
        PaisVisitado(
            pais_codigo="PT",
            primeira_visita=date(2025, 5, 1),
            ultima_visita=date(2026, 2, 1),
            total_viagens=2,
        ),
    ]


def test_paradas_futuras_nao_entram_nem_no_periodo_do_pais():
    resultado = paises_visitados(
        [parada("PT", date(2026, 1, 1)), parada("PT", date(2027, 1, 1), StatusViagem.CONFIRMADA)],
        HOJE,
    )

    assert [(p.pais_codigo, p.ultima_visita) for p in resultado] == [("PT", date(2026, 1, 1))]


def test_sem_paradas_validas_retorna_lista_vazia():
    assert paises_visitados([], HOJE) == []
    assert paises_visitados([parada(status=StatusViagem.PLANEJANDO)], HOJE) == []
