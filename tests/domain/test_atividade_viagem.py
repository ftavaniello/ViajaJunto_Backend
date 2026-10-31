from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest

from app.domain.entities.atividade_viagem import AtividadeViagem
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.errors import DadosInvalidos


def atividade(**campos):
    destino = DestinoCatalogo(id=1, nome="Lisboa", pais_codigo="PT")
    catalogo = AtividadeCatalogo(id=1, destino=destino, nome="Museu", categoria="cultura")
    return AtividadeViagem(
        **{
            "viagem_id": 1,
            "destino_viagem_id": 1,
            "atividade": catalogo,
            "data": date(2027, 7, 3),
            **campos,
        }
    )


@pytest.mark.parametrize(
    "campos",
    [
        {"data": None},
        {"data": datetime(2027, 7, 3)},
        {"hora_inicio": "09:00"},
        {"hora_inicio": time(9, tzinfo=timezone.utc)},
        {"duracao_minutos": 0},
        {"duracao_minutos": -1},
        {"duracao_minutos": True},
        {"duracao_minutos": 2147483648},
        {"custo_previsto": Decimal("-0.01")},
        {"custo_previsto": Decimal("1.001")},
        {"custo_previsto": Decimal("NaN")},
        {"custo_previsto": Decimal("Infinity")},
        {"custo_previsto": Decimal("10000000000")},
        {"custo_previsto": 0.1},
        {"status": "inexistente"},
        {"status": "concluida"},
    ],
)
def test_atividade_invalida(campos):
    with pytest.raises(DadosInvalidos):
        atividade(**campos)


def test_custo_decimal_e_limites():
    assert atividade(custo_previsto=Decimal("0.10")).custo_previsto == Decimal("0.10")
    assert atividade(custo_previsto=Decimal("9999999999.99")).custo_previsto == Decimal(
        "9999999999.99"
    )
    assert atividade().status.value == "pendente"
    assert atividade().catalogo_atividade_id == 1


def test_conclusao_exige_comprovacao_e_preserva_legado():
    agora = datetime(2026, 10, 31, tzinfo=timezone.utc)
    concluida = atividade(status="concluida", realizada_em=agora, realizada_por_id=1)
    assert concluida.status.value == "concluida"
    assert atividade(status="cancelada").status.value == "cancelada"


@pytest.mark.parametrize(
    "campos",
    [
        {"viagem_id": 2},
        {"destino_viagem_id": 2},
        {"data": date(2027, 7, 1)},
    ],
)
def test_vinculo_e_periodo_do_destino(campos):
    planejada = atividade(**campos)
    parada = DestinoViagem(
        id=1,
        viagem_id=1,
        destino=planejada.atividade.destino,
        ordem=1,
        data_chegada=date(2027, 7, 2),
        data_saida=date(2027, 7, 5),
    )
    with pytest.raises(DadosInvalidos):
        planejada.validar_destino(parada)
