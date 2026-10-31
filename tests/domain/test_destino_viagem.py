from datetime import date, datetime

import pytest

from app.domain.entities.catalogo import DestinoCatalogo
from app.domain.entities.destino_viagem import DestinoViagem, validar_reordenacao
from app.domain.errors import DadosInvalidos


def parada(**campos):
    return DestinoViagem(
        **{
            "viagem_id": 1,
            "destino": DestinoCatalogo(id=1, nome="Lisboa", pais_codigo="PT"),
            "ordem": 1,
            "data_chegada": date(2027, 7, 2),
            "data_saida": date(2027, 7, 5),
            **campos,
        }
    )


@pytest.mark.parametrize(
    "campos",
    [
        {"ordem": 0},
        {"ordem": True},
        {"data_saida": date(2027, 7, 1)},
        {"data_chegada": datetime(2027, 7, 2)},
        {"data_saida": None},
        {"descricao": "x" * 10001},
        {"hospedagem": "x" * 256},
    ],
)
def test_destino_viagem_invalido(campos):
    with pytest.raises(DadosInvalidos):
        parada(**campos)


def test_periodo_e_textos_da_parada():
    destino = parada(descricao="  Particular  ", hospedagem=" ")
    destino.validar_periodo(date(2027, 7, 1), date(2027, 7, 20))
    assert destino.descricao == "Particular"
    assert destino.hospedagem is None
    assert destino.destino_catalogo_id == 1
    mesmo_dia = parada(data_saida=date(2027, 7, 2))
    mesmo_dia.validar_periodo(date(2027, 7, 2), date(2027, 7, 2))


@pytest.mark.parametrize(
    "inicio,fim",
    [
        (date(2027, 7, 3), date(2027, 7, 20)),
        (date(2027, 7, 1), date(2027, 7, 4)),
    ],
)
def test_destino_fora_periodo(inicio, fim):
    destino = parada()
    with pytest.raises(DadosInvalidos):
        destino.validar_periodo(inicio, fim)


@pytest.mark.parametrize("ids", [[1, 1], [], [2], [True]])
def test_ordem_invalida(ids):
    destinos = [parada(id=1)]
    with pytest.raises(DadosInvalidos):
        validar_reordenacao(ids, destinos)


def test_ordem_completa_e_roteiro_vazio():
    validar_reordenacao([2, 1], [parada(id=1), parada(id=2, ordem=2)])
    validar_reordenacao([], [])
