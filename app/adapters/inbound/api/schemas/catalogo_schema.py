from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import CategoriaAtividade


class DestinoCatalogoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    pais_codigo: str
    latitude: Decimal | None
    longitude: Decimal | None
    foto_url: str | None
    google_place_id: str | None


class ReviewCatalogoResponse(BaseModel):
    """Contrato reservado para a integração da issue #23."""

    id: int
    nota: int = Field(ge=1, le=5)
    comentario: str | None
    autor_nome: str | None
    criado_em: datetime


class AtividadeCatalogoResponse(BaseModel):
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
    avaliacoes_disponiveis: bool = Field(default=False, description="Integração pendente na #23.")
    media_avaliacoes: float | None = Field(default=None, ge=1, le=5)
    total_avaliacoes: int | None = Field(default=None, ge=0)
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
    destino_catalogo_id: int | None = Field(default=None, ge=1)
    pagina: int = Field(default=1, ge=1)
    tamanho_pagina: int = Field(default=20, ge=1, le=100)
