from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlsplit

from app.domain.enums import CategoriaAtividade
from app.domain.errors import DadosInvalidos


def texto(valor: str | None, campo: str, limite: int, obrigatorio: bool = False) -> str | None:
    if valor is None and not obrigatorio:
        return None
    if not isinstance(valor, str) or (obrigatorio and not valor.strip()):
        raise DadosInvalidos(f"{campo} inválido")
    valor = valor.strip()
    if len(valor) > limite:
        raise DadosInvalidos(f"{campo} deve ter no máximo {limite} caracteres")
    return valor or None


def validar_local(latitude: Decimal | None, longitude: Decimal | None, foto_url: str | None):
    for valor, limite in ((latitude, 90), (longitude, 180)):
        if valor is not None and (not Decimal(valor).is_finite() or not -limite <= valor <= limite):
            raise DadosInvalidos("Coordenadas inválidas")
    if foto_url:
        try:
            url = urlsplit(foto_url)
            valido = url.scheme in {"http", "https"} and bool(url.hostname)
        except ValueError:
            valido = False
        if not valido:
            raise DadosInvalidos("Foto deve ser uma URL HTTP ou HTTPS")


@dataclass(frozen=True, kw_only=True)
class DestinoCatalogo:
    nome: str
    pais_codigo: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    foto_url: str | None = None
    google_place_id: str | None = None
    id: int | None = None

    def __post_init__(self):
        object.__setattr__(self, "nome", texto(self.nome, "Nome", 255, True))
        if not isinstance(self.pais_codigo, str) or not (
            len(self.pais_codigo) == 2
            and self.pais_codigo.isascii()
            and self.pais_codigo.isalpha()
            and self.pais_codigo.isupper()
        ):
            raise DadosInvalidos("País deve ser um código ISO alfa-2 em maiúsculas")
        for campo, limite in (("foto_url", 500), ("google_place_id", 255)):
            object.__setattr__(self, campo, texto(getattr(self, campo), campo, limite))
        validar_local(self.latitude, self.longitude, self.foto_url)


@dataclass(frozen=True, kw_only=True)
class AtividadeCatalogo:
    destino: DestinoCatalogo
    nome: str
    categoria: CategoriaAtividade
    descricao: str | None = None
    endereco: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    foto_url: str | None = None
    google_place_id: str | None = None
    fonte: str = "manual"
    id: int | None = None

    def __post_init__(self):
        for campo, limite, obrigatorio in (
            ("nome", 255, True),
            ("descricao", 10000, False),
            ("endereco", 255, False),
            ("foto_url", 500, False),
            ("google_place_id", 255, False),
        ):
            object.__setattr__(self, campo, texto(getattr(self, campo), campo, limite, obrigatorio))
        try:
            object.__setattr__(self, "categoria", CategoriaAtividade(self.categoria))
        except (ValueError, TypeError) as error:
            raise DadosInvalidos("Categoria de atividade inválida") from error
        if self.fonte != "manual":
            raise DadosInvalidos("Origem não suportada; use curadoria manual")
        validar_local(self.latitude, self.longitude, self.foto_url)
