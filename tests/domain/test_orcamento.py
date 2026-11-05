from decimal import Decimal

import pytest

from app.domain.entities.orcamento import Orcamento, ResumoFinanceiro
from app.domain.enums import CategoriaAtividade
from app.domain.errors import DadosInvalidos


def resumo(valor_total, **custos):
    orcamento = None if valor_total is None else Orcamento(viagem_id=1, valor_total=valor_total)
    return ResumoFinanceiro.calcular(
        1, orcamento, {CategoriaAtividade(c): Decimal(v) for c, v in custos.items()}
    )


def categoria(resultado, nome):
    return next(c for c in resultado.categorias if c.categoria == nome)


def test_orcamento_normaliza_duas_casas():
    assert Orcamento(viagem_id=1, valor_total=Decimal("1000")).valor_total == Decimal("1000.00")
    assert str(Orcamento(viagem_id=1, valor_total=Decimal("0")).valor_total) == "0.00"


@pytest.mark.parametrize(
    "valor",
    [
        Decimal("-0.01"),
        Decimal("1.001"),
        Decimal("10000000000.00"),
        Decimal("NaN"),
        Decimal("Infinity"),
        1000,
        1000.0,
        "1000",
        None,
    ],
)
def test_orcamento_rejeita_valor_invalido(valor):
    with pytest.raises(DadosInvalidos):
        Orcamento(viagem_id=1, valor_total=valor)


def test_exemplo_da_issue_1000_menos_300_sobra_700():
    resultado = resumo(Decimal("1000"), passeio="200", hospedagem="100")

    assert resultado.orcamento_total == Decimal("1000.00")
    assert resultado.total_planejado == Decimal("300.00")
    assert resultado.saldo_disponivel == Decimal("700.00")
    assert resultado.percentual_consumido == Decimal("30.00")
    assert resultado.orcamento_excedido is False
    cultura = categoria(resultado, "passeio")
    assert cultura.total_planejado == Decimal("200.00")
    assert cultura.percentual_orcamento == Decimal("20.00")
    assert cultura.percentual_planejado == Decimal("66.67")


def test_todas_as_categorias_aparecem_na_ordem_do_enum_mesmo_zeradas():
    resultado = resumo(Decimal("100"), hospedagem="10")

    assert [c.categoria for c in resultado.categorias] == list(CategoriaAtividade)
    compras = categoria(resultado, "outro")
    assert compras.total_planejado == Decimal("0.00")
    assert compras.percentual_orcamento == Decimal("0.00")
    assert compras.percentual_planejado == Decimal("0.00")


def test_sem_atividades_saldo_igual_ao_orcamento_e_sem_participacao():
    resultado = resumo(Decimal("500"))

    assert resultado.total_planejado == Decimal("0.00")
    assert resultado.saldo_disponivel == Decimal("500.00")
    assert resultado.percentual_consumido == Decimal("0.00")
    assert all(c.percentual_planejado is None for c in resultado.categorias)


def test_orcamento_zero_nao_divide_por_zero():
    resultado = resumo(Decimal("0"), passeio="50")

    assert resultado.saldo_disponivel == Decimal("-50.00")
    assert resultado.percentual_consumido is None
    assert resultado.orcamento_excedido is True
    assert categoria(resultado, "passeio").percentual_orcamento is None
    assert categoria(resultado, "passeio").percentual_planejado == Decimal("100.00")


def test_orcamento_zero_sem_atividades_nao_esta_excedido():
    resultado = resumo(Decimal("0"))

    assert resultado.saldo_disponivel == Decimal("0.00")
    assert resultado.orcamento_excedido is False


def test_sem_orcamento_definido_mostra_apenas_o_planejado():
    resultado = resumo(None, transporte="80")

    assert resultado.orcamento_total is None
    assert resultado.saldo_disponivel is None
    assert resultado.percentual_consumido is None
    assert resultado.orcamento_excedido is False
    transporte = categoria(resultado, "transporte")
    assert transporte.percentual_orcamento is None
    assert transporte.percentual_planejado == Decimal("100.00")


def test_estouro_gera_saldo_negativo_e_percentual_acima_de_100():
    resultado = resumo(Decimal("1000"), refeicao="900", transporte="350.50")

    assert resultado.total_planejado == Decimal("1250.50")
    assert resultado.saldo_disponivel == Decimal("-250.50")
    assert resultado.percentual_consumido == Decimal("125.05")
    assert resultado.orcamento_excedido is True


def test_gastar_exatamente_o_orcamento_nao_e_estouro():
    resultado = resumo(Decimal("100"), hospedagem="100")

    assert resultado.saldo_disponivel == Decimal("0.00")
    assert resultado.orcamento_excedido is False


@pytest.mark.parametrize(
    ("orcamento", "custo", "esperado"),
    [
        ("3", "1", "33.33"),  # 33,333...
        ("3", "2", "66.67"),  # 66,666...
        ("800", "1", "0.13"),  # 0,125 -> meio para cima
        ("1600", "1", "0.06"),  # 0,0625
        ("0.03", "0.01", "33.33"),
        ("9999999999.99", "0.01", "0.00"),
    ],
)
def test_arredondamento_meio_para_cima_com_duas_casas(orcamento, custo, esperado):
    resultado = resumo(Decimal(orcamento), passeio=custo)

    assert categoria(resultado, "passeio").percentual_orcamento == Decimal(esperado)
    assert str(resultado.percentual_consumido) == esperado


def test_somas_sao_exatas_em_decimal():
    # Em float, 0.1 + 0.2 != 0.3.
    resultado = resumo(Decimal("0.30"), passeio="0.10", hospedagem="0.20")

    assert resultado.total_planejado == Decimal("0.30")
    assert resultado.saldo_disponivel == Decimal("0.00")
    assert resultado.percentual_consumido == Decimal("100.00")
