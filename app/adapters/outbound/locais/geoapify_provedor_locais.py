"""Adaptador da Places API do Geoapify (https://apidocs.geoapify.com/docs/places/).

Só a biblioteca padrão: uma requisição GET por busca, com timeout. A chave vai na
query string, como o Geoapify exige, e por isso nunca entra em mensagens de erro
nem em exceções encadeadas.
"""

import json
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from http.client import HTTPResponse
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.domain.enums import CategoriaAtividade, FonteCatalogo
from app.domain.errors import (
    CredencialProvedorLocaisInvalida,
    LimiteProvedorLocaisExcedido,
    ProvedorLocaisIndisponivel,
)
from app.domain.ports.provedor_locais import LocalExterno, ProvedorLocais

URL_PLACES = "https://api.geoapify.com/v2/places"

# Categorias do catálogo -> chaves de categoria do Geoapify (pai inclui os filhos).
CATEGORIAS_GEOAPIFY: dict[CategoriaAtividade, str] = {
    CategoriaAtividade.PASSEIO: (
        "entertainment.museum,entertainment.culture,tourism.sights,"
        "leisure.park,beach,entertainment.zoo,entertainment.theme_park,tourism.attraction"
    ),
    CategoriaAtividade.REFEICAO: "catering.restaurant,catering.cafe",
    CategoriaAtividade.HOSPEDAGEM: "accommodation",
    CategoriaAtividade.TRANSPORTE: "public_transport",
    CategoriaAtividade.OUTRO: "commercial.shopping_mall,tourism",
}
_SEIS_CASAS = Decimal("0.000001")  # Numeric(9, 6) no banco.
_LIMITE_TEXTO = 255

Abrir = Callable[..., HTTPResponse]


class GeoapifyProvedorLocais(ProvedorLocais):
    def __init__(
        self,
        api_key: str,
        timeout_segundos: float = 10,
        idioma: str = "pt",
        abrir: Abrir = urlopen,
    ):
        if not api_key:
            raise CredencialProvedorLocaisInvalida("Chave do Geoapify não configurada")
        self._api_key = api_key
        self.timeout_segundos = timeout_segundos
        self.idioma = idioma
        self._abrir = abrir

    @property
    def fonte(self) -> FonteCatalogo:
        return FonteCatalogo.GEOAPIFY

    def buscar_proximos(
        self,
        latitude: Decimal,
        longitude: Decimal,
        categoria: CategoriaAtividade,
        raio_metros: int,
        limite: int,
    ) -> list[LocalExterno]:
        parametros = {
            "categories": CATEGORIAS_GEOAPIFY[categoria],
            # O Geoapify usa longitude antes de latitude.
            "filter": f"circle:{longitude},{latitude},{raio_metros}",
            "bias": f"proximity:{longitude},{latitude}",
            "limit": limite,
            "lang": self.idioma,
            "apiKey": self._api_key,
        }
        requisicao = Request(
            f"{URL_PLACES}?{urlencode(parametros)}", headers={"Accept": "application/json"}
        )
        corpo = self._requisitar(requisicao)
        try:
            dados = json.loads(corpo)
            features = dados["features"]
        except (ValueError, TypeError, KeyError):
            raise ProvedorLocaisIndisponivel("Geoapify devolveu uma resposta inválida") from None
        locais = (self._local(f) for f in features if isinstance(f, dict))
        return [local for local in locais if local is not None]

    def _requisitar(self, requisicao: Request) -> bytes:
        # `from None` em todos os casos: as exceções do urllib guardam a URL com a chave.
        try:
            with self._abrir(requisicao, timeout=self.timeout_segundos) as resposta:
                return resposta.read()
        except HTTPError as error:
            status = error.code
            if status in (401, 403):
                raise CredencialProvedorLocaisInvalida(
                    f"Geoapify recusou a chave configurada (HTTP {status})"
                ) from None
            if status == 429:
                raise LimiteProvedorLocaisExcedido(
                    "Limite de requisições do Geoapify atingido; tente mais tarde",
                    _segundos(error.headers.get("Retry-After") if error.headers else None),
                ) from None
            if status >= 500:
                raise ProvedorLocaisIndisponivel(f"Geoapify indisponível (HTTP {status})") from None
            raise ProvedorLocaisIndisponivel(
                f"Geoapify recusou a consulta (HTTP {status})"
            ) from None
        except (URLError, OSError) as error:
            # Timeout na conexão chega embrulhado em URLError; na leitura, direto.
            motivo = error.reason if isinstance(error, URLError) else error
            if isinstance(motivo, TimeoutError):
                raise ProvedorLocaisIndisponivel(
                    f"Geoapify não respondeu em {self.timeout_segundos:g} s"
                ) from None
            raise ProvedorLocaisIndisponivel("Não foi possível conectar ao Geoapify") from None

    @staticmethod
    def _local(feature: dict) -> LocalExterno | None:
        """Converte um item da resposta; itens sem id, nome ou coordenadas são descartados."""
        propriedades = feature.get("properties")
        if not isinstance(propriedades, dict):
            return None
        id_externo, nome = propriedades.get("place_id"), propriedades.get("name")
        if not isinstance(id_externo, str) or not isinstance(nome, str) or not nome.strip():
            return None
        try:
            latitude = Decimal(str(propriedades["lat"])).quantize(_SEIS_CASAS)
            longitude = Decimal(str(propriedades["lon"])).quantize(_SEIS_CASAS)
        except (KeyError, InvalidOperation):
            return None
        endereco = propriedades.get("formatted")
        return LocalExterno(
            id_externo=id_externo,
            nome=nome.strip()[:_LIMITE_TEXTO],
            latitude=latitude,
            longitude=longitude,
            endereco=endereco.strip()[:_LIMITE_TEXTO] if isinstance(endereco, str) else None,
        )


def _segundos(valor: str | None) -> int | None:
    return int(valor) if valor and valor.strip().isdigit() else None
