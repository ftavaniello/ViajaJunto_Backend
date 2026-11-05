"""Adaptador Geoapify sem rede: o `urlopen` é substituído por respostas simuladas."""
import io
import json
import re
import socket
import traceback
from decimal import Decimal
from email.message import Message
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import pytest

from app.adapters.outbound.locais.geoapify_provedor_locais import (
    CATEGORIAS_GEOAPIFY,
    GeoapifyProvedorLocais,
)
from app.domain.enums import CategoriaAtividade, FonteCatalogo
from app.domain.errors import (
    CredencialProvedorLocaisInvalida,
    LimiteProvedorLocaisExcedido,
    ProvedorLocaisIndisponivel,
)
from app.infrastructure.config import ConfiguracaoInvalida, carregar_settings, validar_settings
from app.infrastructure.locais import criar_provedor_locais

CHAVE = "chave-secreta-de-teste"
LAT, LON = Decimal("28.538336"), Decimal("-81.379234")


def feature(**propriedades):
    return {"type": "Feature", "properties": propriedades}


MUSEU = feature(
    place_id="51abc",
    name="Orlando Museum of Art",
    formatted="2416 N Mills Ave, Orlando, FL 32803, United States",
    lat=28.572447,
    lon=-81.365295,
    categories=["entertainment.museum"],
)


class Http:
    """Faz o papel do urlopen: guarda a requisição e devolve uma resposta ou erro."""

    def __init__(self, corpo=None, erro: Exception | None = None):
        self.corpo = corpo if corpo is not None else {"type": "FeatureCollection", "features": []}
        self.erro = erro
        self.requisicoes = []

    def __call__(self, requisicao, timeout):
        self.requisicoes.append((requisicao, timeout))
        if self.erro is not None:
            raise self.erro
        dados = self.corpo if isinstance(self.corpo, bytes) else json.dumps(self.corpo).encode()
        return io.BytesIO(dados)

    def parametros(self) -> dict[str, str]:
        url = self.requisicoes[0][0].full_url
        return {chave: valores[0] for chave, valores in parse_qs(urlsplit(url).query).items()}


def provedor(http: Http) -> GeoapifyProvedorLocais:
    return GeoapifyProvedorLocais(CHAVE, timeout_segundos=7, abrir=http)


def buscar(http: Http, categoria=CategoriaAtividade.PASSEIO):
    return provedor(http).buscar_proximos(LAT, LON, categoria, 2_500, 15)


def erro_http(status: int, cabecalhos: dict | None = None) -> HTTPError:
    headers = Message()
    for nome, valor in (cabecalhos or {}).items():
        headers[nome] = valor
    url = f"https://api.geoapify.com/v2/places?apiKey={CHAVE}"
    return HTTPError(url, status, "erro", headers, io.BytesIO(b"{}"))


def test_monta_a_consulta_com_longitude_primeiro_e_timeout():
    http = Http({"features": [MUSEU]})

    buscar(http)

    requisicao, timeout = http.requisicoes[0]
    assert requisicao.full_url.startswith("https://api.geoapify.com/v2/places?")
    assert timeout == 7
    assert http.parametros() == {
        "categories": (
            "entertainment.museum,entertainment.culture,tourism.sights,"
            "leisure.park,beach,entertainment.zoo,entertainment.theme_park,tourism.attraction"
        ),
        "filter": "circle:-81.379234,28.538336,2500",
        "bias": "proximity:-81.379234,28.538336",
        "limit": "15",
        "lang": "pt",
        "apiKey": CHAVE,
    }


def test_converte_a_resposta_para_o_contrato_do_catalogo():
    locais = buscar(Http({"features": [MUSEU]}))

    assert len(locais) == 1
    museu = locais[0]
    assert museu.id_externo == "51abc"
    assert museu.nome == "Orlando Museum of Art"
    assert museu.endereco == "2416 N Mills Ave, Orlando, FL 32803, United States"
    assert (museu.latitude, museu.longitude) == (Decimal("28.572447"), Decimal("-81.365295"))
    assert provedor(Http()).fonte == FonteCatalogo.GEOAPIFY


def test_descarta_itens_incompletos_e_ajusta_tamanhos():
    longo = "x" * 300
    resposta = {
        "features": [
            feature(place_id="sem-nome", lat=1, lon=1),
            feature(name="Sem id", lat=1, lon=1),
            feature(place_id="sem-coordenada", name="Sem coordenada"),
            feature(place_id="coordenada-ruim", name="Ruim", lat="abc", lon=1),
            "não é um objeto",
            {"type": "Feature"},
            feature(place_id="longo", name=longo, formatted=longo, lat=1.1234567, lon=2),
        ]
    }

    locais = buscar(Http(resposta))

    assert [local.id_externo for local in locais] == ["longo"]
    assert len(locais[0].nome) == len(locais[0].endereco) == 255
    assert locais[0].latitude == Decimal("1.123457")


def test_todas_as_categorias_do_catalogo_tem_mapeamento():
    assert set(CATEGORIAS_GEOAPIFY) == set(CategoriaAtividade)


@pytest.mark.parametrize(
    ("erro", "tipo", "mensagem"),
    [
        (erro_http(401), CredencialProvedorLocaisInvalida, "HTTP 401"),
        (erro_http(403), CredencialProvedorLocaisInvalida, "HTTP 403"),
        (erro_http(429), LimiteProvedorLocaisExcedido, "Limite"),
        (erro_http(500), ProvedorLocaisIndisponivel, "indisponível (HTTP 500)"),
        (erro_http(503), ProvedorLocaisIndisponivel, "indisponível (HTTP 503)"),
        (erro_http(400), ProvedorLocaisIndisponivel, "recusou a consulta (HTTP 400)"),
        (TimeoutError("lento"), ProvedorLocaisIndisponivel, "não respondeu em 7 s"),
        (URLError(socket.timeout("lento")), ProvedorLocaisIndisponivel, "não respondeu"),
        (URLError("sem rede"), ProvedorLocaisIndisponivel, "Não foi possível conectar"),
        (ConnectionResetError(), ProvedorLocaisIndisponivel, "Não foi possível conectar"),
    ],
)
def test_traduz_falhas_para_erros_de_dominio_sem_vazar_a_chave(erro, tipo, mensagem):
    with pytest.raises(tipo, match=re.escape(mensagem)) as capturado:
        buscar(Http(erro=erro))

    assert CHAVE not in str(capturado.value)
    # `from None`: o traceback não traz a exceção original, que guarda a URL com a chave.
    assert CHAVE not in "".join(traceback.format_exception(capturado.value))


def test_limite_informa_quando_tentar_de_novo():
    with pytest.raises(LimiteProvedorLocaisExcedido) as capturado:
        buscar(Http(erro=erro_http(429, {"Retry-After": "120"})))

    assert capturado.value.tentar_em_segundos == 120


@pytest.mark.parametrize("corpo", [b"<html>erro</html>", b"[]", b'{"sem": "features"}'])
def test_resposta_ilegivel(corpo):
    with pytest.raises(ProvedorLocaisIndisponivel, match="resposta inválida"):
        buscar(Http(corpo))


def test_sem_chave_nao_monta_o_adaptador():
    with pytest.raises(CredencialProvedorLocaisInvalida):
        GeoapifyProvedorLocais("")


# --- Configuração -----------------------------------------------------------------


def test_fabrica_usa_chave_do_ambiente():
    config = carregar_settings({"GEOAPIFY_API_KEY": f"  {CHAVE}  ", "LOCAIS_TIMEOUT_SECONDS": "4"})

    adaptador = criar_provedor_locais(config)

    assert isinstance(adaptador, GeoapifyProvedorLocais)
    assert adaptador.timeout_segundos == 4


def test_fabrica_le_a_chave_de_arquivo(tmp_path):
    arquivo = tmp_path / "geoapify.key"
    arquivo.write_text(f"{CHAVE}\n", encoding="utf-8")

    adaptador = criar_provedor_locais(carregar_settings({"GEOAPIFY_API_KEY_FILE": str(arquivo)}))

    assert isinstance(adaptador, GeoapifyProvedorLocais)


@pytest.mark.parametrize(
    "env", [{}, {"GEOAPIFY_API_KEY": "  "}, {"GEOAPIFY_API_KEY_FILE": "/nao/existe.key"}]
)
def test_fabrica_sem_chave_explica_o_que_configurar(env):
    with pytest.raises(CredencialProvedorLocaisInvalida, match="GEOAPIFY_API_KEY"):
        criar_provedor_locais(carregar_settings(env))


def test_api_sobe_sem_chave_mas_recusa_timeout_invalido():
    validar_settings(carregar_settings({}))
    with pytest.raises(ConfiguracaoInvalida, match="LOCAIS_TIMEOUT_SECONDS"):
        validar_settings(carregar_settings({"LOCAIS_TIMEOUT_SECONDS": "0"}))


def test_busca_hospedagem_usa_accommodation():
    http = Http()
    buscar(http, CategoriaAtividade.HOSPEDAGEM)
    assert http.parametros()["categories"] == "accommodation"
