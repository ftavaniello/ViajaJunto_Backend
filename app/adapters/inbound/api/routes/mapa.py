from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.adapters.inbound.api.schemas.mapa_schema import (
    MapaViagemResponse,
    PaisesVisitadosResponse,
    PaisVisitadoResponse,
    PontoMapaResponse,
)
from app.adapters.inbound.api.security import get_usuario_atual
from app.application.use_cases.consultar_mapa import ConsultarMapaViagem, ConsultarPaisesVisitados
from app.domain.entities.usuario import Usuario
from app.infrastructure.dependencies import (
    get_consultar_mapa_viagem,
    get_consultar_paises_visitados,
)

router = APIRouter(tags=["Mapa"])
UsuarioAtual = Annotated[Usuario, Depends(get_usuario_atual)]
IdPositivo = Annotated[int, Path(ge=1)]
_NAO_AUTENTICADO = {401: {"description": "Token ausente, inválido ou expirado"}}


@router.get(
    "/usuarios/me/paises-visitados",
    response_model=PaisesVisitadosResponse,
    summary="Lista os países que o usuário autenticado já visitou",
    description="Somente do próprio usuário do token. Conta paradas de viagens próprias "
    "ou compartilhadas, com status `confirmada` ou `concluida` e data de chegada até "
    "hoje (UTC). Cada país aparece uma vez. Ver docs/mapa-paises-visitados.md.",
    responses=_NAO_AUTENTICADO,
)
def paises_visitados(
    usuario: UsuarioAtual,
    caso: Annotated[ConsultarPaisesVisitados, Depends(get_consultar_paises_visitados)],
):
    paises = caso.execute(usuario.id)
    return PaisesVisitadosResponse(
        total=len(paises), paises=[PaisVisitadoResponse.model_validate(p) for p in paises]
    )


@router.get(
    "/viagens/{viagem_id}/mapa",
    response_model=MapaViagemResponse,
    summary="Pontos do roteiro da viagem para o mapa",
    description="Criador e colaboradores consultam. Paradas na ordem de visita, com "
    "coordenadas do destino do catálogo. O desenho do mapa e dos marcadores é do frontend.",
    responses={
        **_NAO_AUTENTICADO,
        404: {"description": "Viagem inexistente ou da qual o usuário não participa"},
    },
)
def mapa_viagem(
    viagem_id: IdPositivo,
    usuario: UsuarioAtual,
    caso: Annotated[ConsultarMapaViagem, Depends(get_consultar_mapa_viagem)],
):
    return MapaViagemResponse(
        viagem_id=viagem_id,
        paradas=[
            PontoMapaResponse(
                parada_id=parada.id,
                destino_catalogo_id=parada.destino_catalogo_id,
                ordem=parada.ordem,
                nome=parada.destino.nome,
                pais_codigo=parada.destino.pais_codigo,
                latitude=parada.destino.latitude,
                longitude=parada.destino.longitude,
                data_chegada=parada.data_chegada,
                data_saida=parada.data_saida,
            )
            for parada in caso.execute(viagem_id, usuario.id)
        ],
    )
