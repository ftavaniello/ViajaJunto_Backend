from datetime import date, datetime

from pydantic import BaseModel, Field

from app.domain.enums import StatusViagem


class CriarViagemRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=255, examples=["Mochilão na Europa"])
    descricao: str | None = Field(default=None, examples=["Férias de julho com a turma"])
    data_inicio: date = Field(examples=["2027-07-01"])
    data_fim: date = Field(
        examples=["2027-07-20"], description="Não pode ser anterior a `data_inicio`."
    )


class AtualizarViagemRequest(BaseModel):
    nome: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        examples=["Mochilão na Europa"],
        description="Campos omitidos (ou nulos) permanecem inalterados.",
    )
    descricao: str | None = Field(
        default=None,
        examples=["Férias de julho com a turma"],
        description="Envie uma string vazia para remover a descrição.",
    )
    data_inicio: date | None = Field(default=None, examples=["2027-07-01"])
    data_fim: date | None = Field(default=None, examples=["2027-07-20"])
    status: StatusViagem | None = Field(default=None, examples=[StatusViagem.CONFIRMADA])


class ViagemResponse(BaseModel):
    id: int = Field(examples=[1])
    criador_id: int = Field(examples=[1])
    nome: str = Field(examples=["Mochilão na Europa"])
    descricao: str | None = Field(examples=["Férias de julho com a turma"])
    data_inicio: date = Field(examples=["2027-07-01"])
    data_fim: date = Field(examples=["2027-07-20"])
    status: StatusViagem = Field(examples=[StatusViagem.PLANEJANDO])
    criado_em: datetime | None = Field(examples=["2026-10-29T12:00:00Z"])
    atualizado_em: datetime | None = Field(examples=["2026-10-29T12:00:00Z"])
