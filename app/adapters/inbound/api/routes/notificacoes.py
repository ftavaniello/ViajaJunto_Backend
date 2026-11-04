from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.adapters.inbound.api.schemas.notificacao_schema import (
    ContagemNaoLidasResponse,
    MarcarTodasLidasResponse,
    NotificacaoResponse,
    PaginaNotificacoesResponse,
)
from app.adapters.inbound.api.security import get_usuario_atual
from app.application.use_cases.gerenciar_notificacoes import GerenciarNotificacoes
from app.domain.entities.notificacao import Notificacao
from app.domain.entities.usuario import Usuario
from app.infrastructure.dependencies import get_gerenciar_notificacoes

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])
UsuarioAtual = Annotated[Usuario, Depends(get_usuario_atual)]
CasoNotificacoes = Annotated[GerenciarNotificacoes, Depends(get_gerenciar_notificacoes)]
_NAO_AUTENTICADO = {401: {"description": "Token ausente, inválido ou expirado"}}


def _to_response(notificacao: Notificacao) -> NotificacaoResponse:
    return NotificacaoResponse(
        id=notificacao.id,
        tipo=notificacao.tipo,
        mensagem=notificacao.mensagem,
        viagem_id=notificacao.viagem_id,
        ator_id=notificacao.ator_id,
        lida=notificacao.lida,
        lida_em=notificacao.lida_em,
        criado_em=notificacao.criado_em,
    )


@router.get(
    "",
    response_model=PaginaNotificacoesResponse,
    summary="Lista as notificações do usuário",
    description=(
        "Somente as do usuário autenticado. Não lidas primeiro, depois as mais recentes. "
        "Inclui o total de não lidas, para o frontend atualizar o contador."
    ),
    responses=_NAO_AUTENTICADO,
)
def listar(
    usuario: UsuarioAtual,
    caso: CasoNotificacoes,
    nao_lidas: bool = Query(default=False, description="Retorna só as não lidas."),
    pagina: int = Query(default=1, ge=1, description="Número da página, começando em 1."),
    tamanho_pagina: int = Query(default=20, ge=1, le=100, description="Itens por página."),
):
    resultado = caso.listar(usuario.id, nao_lidas, pagina, tamanho_pagina)
    return PaginaNotificacoesResponse(
        itens=[_to_response(n) for n in resultado.itens],
        pagina=resultado.pagina,
        tamanho_pagina=resultado.tamanho_pagina,
        tem_proxima=resultado.tem_proxima,
        nao_lidas=resultado.nao_lidas,
    )


@router.get(
    "/nao-lidas/contagem",
    response_model=ContagemNaoLidasResponse,
    summary="Conta as notificações não lidas",
    description="Consulta leve para polling do contador (sugestão: a cada 30 a 60 segundos).",
    responses=_NAO_AUTENTICADO,
)
def contar_nao_lidas(usuario: UsuarioAtual, caso: CasoNotificacoes):
    return ContagemNaoLidasResponse(nao_lidas=caso.contar_nao_lidas(usuario.id))


@router.patch(
    "/{notificacao_id}/lida",
    response_model=NotificacaoResponse,
    summary="Marca uma notificação como lida",
    description="Idempotente: marcar de novo mantém a data da primeira leitura.",
    responses={
        **_NAO_AUTENTICADO,
        404: {"description": "Notificação inexistente ou de outro usuário"},
    },
)
def marcar_lida(
    notificacao_id: Annotated[int, Path(ge=1)], usuario: UsuarioAtual, caso: CasoNotificacoes
):
    return _to_response(caso.marcar_lida(usuario.id, notificacao_id))


@router.post(
    "/marcar-todas-lidas",
    response_model=MarcarTodasLidasResponse,
    summary="Marca todas as notificações como lidas",
    description="Afeta somente as notificações do usuário autenticado.",
    responses=_NAO_AUTENTICADO,
)
def marcar_todas_lidas(usuario: UsuarioAtual, caso: CasoNotificacoes):
    return MarcarTodasLidasResponse(marcadas=caso.marcar_todas_lidas(usuario.id))
