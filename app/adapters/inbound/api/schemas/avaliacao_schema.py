from pydantic import BaseModel, ConfigDict, Field


class AvaliarAtividadeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nota: int = Field(strict=True, ge=1, le=5, examples=[5])
    comentario: str | None = Field(default=None, max_length=2000, examples=["Gostei da visita."])


class FiltrosAvaliacoes(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pagina: int = Field(default=1, ge=1)
    tamanho_pagina: int = Field(default=20, ge=1, le=100)
