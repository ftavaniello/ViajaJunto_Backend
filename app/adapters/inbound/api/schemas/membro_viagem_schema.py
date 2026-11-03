from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums import PapelMembro
from app.domain.permissoes import PerfilViagem


class ConvidarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(
        examples=["ana@example.com"],
        description="Email do convidado. Ele não precisa ter conta ainda.",
    )


class ConviteResponse(BaseModel):
    id: int = Field(examples=[1])
    email: str = Field(examples=["ana@example.com"])
    expira_em: datetime = Field(examples=["2026-11-10T12:00:00Z"])
    criado_em: datetime | None = Field(examples=["2026-11-03T12:00:00Z"])


class AceitarConviteRequest(BaseModel):
    # Campos extras (como `papel` ou `viagem_id`) sao recusados: o convite define
    # a viagem e quem entra nao escolhe o proprio papel.
    model_config = ConfigDict(extra="forbid")

    token: str = Field(
        min_length=1,
        max_length=128,
        examples=["x8Fq3...token-do-link"],
        description="Valor do parâmetro `token` do link recebido por email.",
    )


class AlterarPapelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    papel: PapelMembro = Field(examples=[PapelMembro.EDITOR])


class MembroViagemResponse(BaseModel):
    usuario_id: int = Field(examples=[2])
    nome: str = Field(examples=["Ana"])
    email: str = Field(examples=["ana@example.com"])
    papel: PerfilViagem = Field(examples=[PerfilViagem.EDITOR])
    entrou_em: datetime | None = Field(examples=["2026-10-29T12:00:00Z"])
