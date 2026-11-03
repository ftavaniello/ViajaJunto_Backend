from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.adapters.inbound.api.routes.viagem import _to_response as _viagem_to_response
from app.adapters.inbound.api.schemas.membro_viagem_schema import (
    AceitarConviteRequest,
    AlterarPapelRequest,
    ConvidarRequest,
    ConviteResponse,
    MembroViagemResponse,
)
from app.adapters.inbound.api.schemas.viagem_schema import ItemListaViagensResponse
from app.adapters.inbound.api.security import get_usuario_atual
from app.application.use_cases.gerenciar_membros_viagem import GerenciarMembrosViagem
from app.domain.entities.convite_viagem import ConviteViagem
from app.domain.entities.usuario import Usuario
from app.domain.membro_viagem import ParticipanteViagem
from app.domain.permissoes import PerfilViagem
from app.infrastructure.dependencies import get_gerenciar_membros_viagem

router = APIRouter(prefix="/viagens", tags=["Colaboradores"])
UsuarioAtual = Annotated[Usuario, Depends(get_usuario_atual)]
CasoMembros = Annotated[GerenciarMembrosViagem, Depends(get_gerenciar_membros_viagem)]
IdPositivo = Annotated[int, Path(ge=1)]
_NAO_AUTENTICADO = {401: {"description": "Token ausente, inválido ou expirado"}}
_LEITURA = {
    **_NAO_AUTENTICADO,
    404: {"description": "Viagem inexistente ou da qual o usuário não participa"},
}
_SOMENTE_CRIADOR = {
    **_LEITURA,
    403: {"description": "Somente o criador gerencia convites e colaboradores"},
}
_GESTAO_MEMBRO = {
    **_SOMENTE_CRIADOR,
    400: {"description": "Tentativa de alterar ou remover o criador"},
    404: {"description": "Viagem inacessível ou usuário não é colaborador desta viagem"},
}


def _convite(convite: ConviteViagem) -> ConviteResponse:
    return ConviteResponse(
        id=convite.id,
        email=convite.email,
        expira_em=convite.expira_em,
        criado_em=convite.criado_em,
    )


def _membro(participante: ParticipanteViagem) -> MembroViagemResponse:
    return MembroViagemResponse(
        usuario_id=participante.usuario_id,
        nome=participante.nome,
        email=participante.email,
        papel=participante.perfil,
        entrou_em=participante.entrou_em,
    )


@router.post(
    "/{viagem_id}/convites",
    response_model=ConviteResponse,
    status_code=201,
    summary="Convida alguém por email",
    description=(
        "Somente o criador. Envia ao email um link de uso único, válido por 7 dias. "
        "O email não precisa ter conta. Convidar de novo o mesmo email invalida o link anterior."
    ),
    responses={
        **_SOMENTE_CRIADOR,
        409: {"description": "O email já é do criador ou de um colaborador da viagem"},
        503: {"description": "Falha ao enviar o email; nada foi gravado"},
    },
)
def convidar(
    viagem_id: IdPositivo, request: ConvidarRequest, usuario: UsuarioAtual, caso: CasoMembros
):
    return _convite(caso.convidar(viagem_id, usuario.id, request.email))


@router.get(
    "/{viagem_id}/convites",
    response_model=list[ConviteResponse],
    summary="Lista os convites pendentes",
    description="Somente o criador. Convites aceitos ou expirados não aparecem.",
    responses=_SOMENTE_CRIADOR,
)
def listar_convites(viagem_id: IdPositivo, usuario: UsuarioAtual, caso: CasoMembros):
    return [_convite(c) for c in caso.listar_convites(viagem_id, usuario.id)]


@router.delete(
    "/{viagem_id}/convites/{convite_id}",
    status_code=204,
    summary="Cancela um convite pendente",
    description="Somente o criador. O link enviado deixa de funcionar.",
    responses={
        **_SOMENTE_CRIADOR,
        404: {"description": "Viagem inacessível ou convite pendente inexistente"},
    },
)
def cancelar_convite(
    viagem_id: IdPositivo, convite_id: IdPositivo, usuario: UsuarioAtual, caso: CasoMembros
):
    caso.cancelar_convite(viagem_id, usuario.id, convite_id)


@router.post(
    "/convites/aceitar",
    response_model=ItemListaViagensResponse,
    status_code=201,
    summary="Aceita um convite recebido por email",
    description=(
        "Recebe o `token` do link. O usuário do token de acesso precisa ser o dono do "
        "email convidado e entra como `visualizador`; só o criador pode promovê-lo depois."
    ),
    responses={
        **_NAO_AUTENTICADO,
        403: {"description": "O convite foi enviado para outro email"},
        404: {"description": "Link inexistente ou expirado"},
        409: {"description": "Convite já utilizado ou usuário já participa da viagem"},
    },
)
def aceitar_convite(request: AceitarConviteRequest, usuario: UsuarioAtual, caso: CasoMembros):
    participacao = caso.aceitar_convite(request.token, usuario.id)
    return ItemListaViagensResponse(
        **_viagem_to_response(participacao.viagem).model_dump(),
        papel_usuario=PerfilViagem(participacao.papel_membro.value),
    )


@router.get(
    "/{viagem_id}/membros",
    response_model=list[MembroViagemResponse],
    summary="Lista os participantes da viagem",
    description="Criador e colaboradores. O criador vem primeiro; os demais por ordem de entrada.",
    responses=_LEITURA,
)
def listar_membros(viagem_id: IdPositivo, usuario: UsuarioAtual, caso: CasoMembros):
    return [_membro(p) for p in caso.listar_membros(viagem_id, usuario.id)]


@router.patch(
    "/{viagem_id}/membros/{membro_id}",
    response_model=MembroViagemResponse,
    summary="Altera o papel de um colaborador",
    description="Somente o criador. Vale a partir da próxima requisição do colaborador.",
    responses=_GESTAO_MEMBRO,
)
def alterar_papel(
    viagem_id: IdPositivo,
    membro_id: IdPositivo,
    request: AlterarPapelRequest,
    usuario: UsuarioAtual,
    caso: CasoMembros,
):
    return _membro(caso.alterar_papel(viagem_id, usuario.id, membro_id, request.papel))


@router.delete(
    "/{viagem_id}/membros/{membro_id}",
    status_code=204,
    summary="Remove um colaborador da viagem",
    description="Somente o criador. O removido perde o acesso na próxima requisição.",
    responses=_GESTAO_MEMBRO,
)
def remover_membro(
    viagem_id: IdPositivo, membro_id: IdPositivo, usuario: UsuarioAtual, caso: CasoMembros
):
    caso.remover_membro(viagem_id, usuario.id, membro_id)
