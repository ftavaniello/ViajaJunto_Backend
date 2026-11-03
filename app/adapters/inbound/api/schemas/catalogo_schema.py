from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import CategoriaAtividade, CategoriaDestino


class DestinoCatalogoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    pais_codigo: str
    categoria: CategoriaDestino
    descricao: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    foto_url: str | None
    google_place_id: str | None


class ReviewCatalogoResponse(BaseModel):
    """Projeção pública: sem email, identidade técnica ou dados privados da viagem."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nota: int = Field(ge=1, le=5)
    comentario: str | None
    autor_nome: str | None
    criado_em: datetime


class DadosAtividadeCatalogoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    descricao: str | None
    categoria: CategoriaAtividade
    endereco: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    foto_url: str | None
    google_place_id: str | None
    fonte: str
    destino: DestinoCatalogoResponse


class AtividadeCatalogoResponse(DadosAtividadeCatalogoResponse):
    media_avaliacoes: float | None = Field(default=None, ge=1, le=5)
    total_avaliacoes: int = Field(default=0, ge=0)
    reviews: list[ReviewCatalogoResponse] = Field(default_factory=list)


class PaginaAtividadesResponse(BaseModel):
    itens: list[AtividadeCatalogoResponse]
    pagina: int
    tamanho_pagina: int
    tem_proxima: bool


class FiltrosCatalogo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str | None = Field(default=None, max_length=255)
    categoria: CategoriaAtividade | None = None
    localizacao: str | None = Field(
        default=None,
        max_length=255,
        description="Trecho do nome da cidade, código de país ou endereço, sem distinguir caixa.",
    )
    nota_minima: Decimal | None = Field(
        default=None,
        ge=1,
        le=5,
        allow_inf_nan=False,
        description="Média mínima inclusiva; atividades sem avaliações não correspondem.",
    )
    destino_catalogo_id: int | None = Field(default=None, ge=1)
    pagina: int = Field(default=1, ge=1)
    tamanho_pagina: int = Field(default=20, ge=1, le=100)


class PaginaDestinosResponse(BaseModel):
    itens: list[DestinoCatalogoResponse]
    pagina: int
    tamanho_pagina: int
    tem_proxima: bool


class FiltrosDestinosCatalogo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str | None = Field(default=None, max_length=255)
    pais_codigo: str | None = Field(
        default=None,
        pattern="^[A-Za-z]{2}$",
        description="Código de país ISO alfa-2, como BR ou PT; aceita minúsculas.",
    )
    categoria: CategoriaDestino | None = None
    pagina: int = Field(default=1, ge=1)
    tamanho_pagina: int = Field(default=20, ge=1, le=100)


class PaginaAvaliacoesResponse(BaseModel):
    itens: list[ReviewCatalogoResponse]
    pagina: int
    tamanho_pagina: int
    tem_proxima: bool
