from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.adapters.inbound.api.schemas.catalogo_schema import (
    DestinoCatalogoResponse,
    FiltrosDestinosCatalogo,
    PaginaDestinosResponse,
    RankingDestinosResponse,
)
from app.application.use_cases.consultar_destinos_catalogo import (
    ConsultarDestinoCatalogo,
    ListarDestinosCatalogo,
)
from app.application.use_cases.consultar_ranking_destinos import (
    LIMITE_MAXIMO,
    ConsultarRankingDestinos,
)
from app.infrastructure.dependencies import (
    get_consultar_destino_catalogo,
    get_consultar_ranking_destinos,
    get_listar_destinos_catalogo,
)

router = APIRouter(prefix="/catalogo/destinos", tags=["Catálogo"])


@router.get(
    "",
    response_model=PaginaDestinosResponse,
    summary="Pesquisa destinos do catálogo público",
    description=(
        "Consulta sem autenticação, para selecionar destinos reutilizáveis. "
        "Combina nome parcial sem distinguir caixa, país e categoria por E. "
        "Ordem crescente por id e paginação por deslocamento; mudanças entre "
        "requisições podem alterar as páginas. Não retorna dados privados de viagens."
    ),
)
def listar(
    filtros: Annotated[FiltrosDestinosCatalogo, Query()],
    caso: Annotated[ListarDestinosCatalogo, Depends(get_listar_destinos_catalogo)],
):
    resultado = caso.execute(**filtros.model_dump())
    return PaginaDestinosResponse(
        itens=[DestinoCatalogoResponse.model_validate(d) for d in resultado.itens],
        pagina=resultado.pagina,
        tamanho_pagina=resultado.tamanho_pagina,
        tem_proxima=resultado.tem_proxima,
    )


# Registrada antes de /{destino_id} para "ranking" não ser lido como id.
@router.get(
    "/ranking",
    response_model=RankingDestinosResponse,
    summary="Ranking público dos destinos mais bem avaliados",
    description=(
        "Consulta sem autenticação, para a página inicial. A nota do destino agrega as "
        "avaliações das atividades do catálogo que pertencem a ele. Ordena pela média "
        "bayesiana (decrescente), depois pelo total de avaliações (decrescente) e pelo id "
        "(crescente). Destinos sem avaliação não aparecem. Ver docs/ranking-destinos.md."
    ),
)
def ranking(
    caso: Annotated[ConsultarRankingDestinos, Depends(get_consultar_ranking_destinos)],
    limite: Annotated[
        int, Query(ge=1, le=LIMITE_MAXIMO, description="Quantidade máxima de destinos.")
    ] = 10,
):
    return RankingDestinosResponse.model_validate(caso.execute(limite))


@router.get(
    "/{destino_id}",
    response_model=DestinoCatalogoResponse,
    summary="Consulta um destino do catálogo público",
    description="Dados gerais do destino, sem datas, ordem ou participantes do roteiro.",
    responses={404: {"description": "Destino não encontrado no catálogo"}},
)
def consultar(
    destino_id: Annotated[int, Path(ge=1)],
    caso: Annotated[ConsultarDestinoCatalogo, Depends(get_consultar_destino_catalogo)],
):
    return DestinoCatalogoResponse.model_validate(caso.execute(destino_id))
