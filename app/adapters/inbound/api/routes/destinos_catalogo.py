from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.adapters.inbound.api.schemas.catalogo_schema import (
    DestinoCatalogoResponse,
    FiltrosDestinosCatalogo,
    PaginaDestinosResponse,
)
from app.application.use_cases.consultar_destinos_catalogo import (
    ConsultarDestinoCatalogo,
    ListarDestinosCatalogo,
)
from app.infrastructure.dependencies import (
    get_consultar_destino_catalogo,
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
