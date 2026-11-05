from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.adapters.inbound.api.schemas.catalogo_schema import DestinoCatalogoResponse


class CriarDestinoViagemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    destino_catalogo_id: int = Field(ge=1, strict=True)
    data_chegada: date
    data_saida: date
    descricao: str | None = Field(default=None, max_length=10000)
    hospedagem: str | None = Field(default=None, max_length=255)
    ordem: int | None = Field(
        default=None,
        ge=1,
        strict=True,
        description="Posição de inserção; omitida, adiciona ao fim.",
    )


class AtualizarDestinoViagemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data_chegada: date | None = None
    data_saida: date | None = None
    descricao: str | None = Field(
        default=None,
        max_length=10000,
        description="Nulo/omitido preserva; vazio remove a descrição.",
    )
    hospedagem: str | None = Field(default=None, max_length=255)


class ReordenarDestinosRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    destinos_ids: list[Annotated[int, Field(ge=1, strict=True)]] = Field(
        description="Todos os IDs de paradas desta viagem, exatamente uma vez, na nova ordem.",
    )


class DestinoViagemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    viagem_id: int
    destino_catalogo_id: int
    destino: DestinoCatalogoResponse
    ordem: int
    data_chegada: date
    data_saida: date
    descricao: str | None
    hospedagem: str | None
