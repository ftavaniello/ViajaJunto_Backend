from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import TipoNotificacao


class NotificacaoResponse(BaseModel):
    id: int = Field(examples=[1])
    tipo: TipoNotificacao = Field(examples=[TipoNotificacao.ATIVIDADE_ALTERADA])
    mensagem: str = Field(
        examples=['Bruno alterou a data da atividade "Museu" em Lisboa (03/07/2027) '
                  'na viagem "Europa".']
    )
    viagem_id: int | None = Field(
        examples=[1], description="Nulo quando a viagem foi excluída."
    )
    ator_id: int | None = Field(
        examples=[2], description="Quem fez a alteração; nulo se a conta foi excluída."
    )
    lida: bool = Field(examples=[False])
    lida_em: datetime | None = Field(examples=[None])
    criado_em: datetime = Field(examples=["2026-11-03T12:00:00Z"])


class PaginaNotificacoesResponse(BaseModel):
    itens: list[NotificacaoResponse]
    pagina: int = Field(ge=1, examples=[1])
    tamanho_pagina: int = Field(ge=1, le=100, examples=[20])
    tem_proxima: bool = Field(examples=[False])
    nao_lidas: int = Field(ge=0, examples=[3], description="Total de não lidas do usuário.")


class ContagemNaoLidasResponse(BaseModel):
    nao_lidas: int = Field(ge=0, examples=[3])


class MarcarTodasLidasResponse(BaseModel):
    marcadas: int = Field(ge=0, examples=[3], description="Quantas estavam não lidas.")
