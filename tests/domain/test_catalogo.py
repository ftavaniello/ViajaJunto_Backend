from dataclasses import replace
from decimal import Decimal

import pytest

from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.enums import CategoriaAtividade
from app.domain.errors import DadosInvalidos


@pytest.fixture
def destino():
    return DestinoCatalogo(nome="Lisboa", pais_codigo="PT")


def test_catalogo_preserva_descricao_foto_e_referencia(destino):
    atividade = AtividadeCatalogo(
        destino=destino,
        nome=" Museu ",
        categoria="cultura",
        descricao=" História ",
        foto_url="https://example.com/museu.jpg",
        google_place_id="referencia-curada",
        latitude=Decimal("38.7"),
        longitude=Decimal("-9.1"),
    )
    assert atividade.nome == "Museu"
    assert atividade.descricao == "História"
    assert atividade.categoria == CategoriaAtividade.CULTURA
    assert atividade.fonte == "manual"
    assert atividade.google_place_id == "referencia-curada"


@pytest.mark.parametrize(
    "mudanca",
    [
        {"nome": " "},
        {"nome": "x" * 256},
        {"categoria": "inexistente"},
        {"latitude": Decimal("91")},
        {"longitude": Decimal("-181")},
        {"latitude": Decimal("NaN")},
        {"foto_url": "javascript:alert(1)"},
        {"google_place_id": "x" * 256},
        {"endereco": "x" * 256},
        {"fonte": "google_places"},
    ],
)
def test_rejeita_atividade_invalida(destino, mudanca):
    with pytest.raises(DadosInvalidos):
        AtividadeCatalogo(
            **{
                "destino": destino,
                "nome": "Museu",
                "categoria": "cultura",
                **mudanca,
            }
        )


@pytest.mark.parametrize("pais", ["pt", "PRT", "", "12", "ÉÉ"])
def test_rejeita_pais_invalido(pais):
    with pytest.raises(DadosInvalidos):
        DestinoCatalogo(nome="Lisboa", pais_codigo=pais)


def test_campos_opcionais_vazios_sao_normalizados(destino):
    atividade = AtividadeCatalogo(destino=destino, nome="Museu", categoria="cultura")
    assert replace(atividade, descricao="   ", foto_url="").descricao is None


@pytest.mark.parametrize("categoria", ["cidade", "praia", "natureza", "cultural"])
def test_destino_categoria_e_descricao(categoria):
    destino = DestinoCatalogo(
        nome=" Destino ",
        pais_codigo="BR",
        categoria=categoria,
        descricao=" Paisagem ",
        latitude=Decimal("-27.5"),
        longitude=Decimal("-48.5"),
        foto_url="https://example.com/destino.jpg",
    )
    assert destino.nome == "Destino"
    assert destino.categoria.value == categoria
    assert destino.descricao == "Paisagem"


@pytest.mark.parametrize(
    "mudanca",
    [
        {"categoria": "hotel"},
        {"categoria": None},
        {"descricao": "x" * 10001},
        {"latitude": Decimal("-91")},
        {"longitude": Decimal("181")},
        {"latitude": Decimal("Infinity")},
        {"foto_url": "file:///segredo"},
    ],
)
def test_destino_rejeita_dados_invalidos(mudanca):
    dados = {"nome": "Destino", "pais_codigo": "BR", **mudanca}
    with pytest.raises(DadosInvalidos):
        DestinoCatalogo(**dados)


def test_destino_compatibilidade_com_categoria_padrao_e_descricao_vazia():
    destino = DestinoCatalogo(nome="Lisboa", pais_codigo="PT", descricao="   ")
    assert destino.categoria.value == "cidade"
    assert destino.descricao is None
