from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.adapters.inbound.api.schemas.catalogo_schema import (
    AtividadeCatalogoResponse,
    FiltrosCatalogo,
    PaginaAtividadesResponse,
)
from app.application.use_cases.consultar_catalogo import (
    ConsultarAtividadeCatalogo,
    ListarAtividadesCatalogo,
)
from app.infrastructure.dependencies import get_consultar_atividade_catalogo, get_listar_catalogo

router = APIRouter(prefix="/catalogo/atividades", tags=["Catálogo"])


@router.get(
    "",
    response_model=PaginaAtividadesResponse,
    summary="Pesquisa atividades do catálogo público",
    description=(
        "Não exige autenticação. Filtros combinados por E; busca textual parcial sem "
        "distinguir maiúsculas e minúsculas. Ordem crescente por id. Paginação por "
        "deslocamento; alterações entre requisições podem mudar as páginas. "
        "Avaliações e filtro por nota estão pendentes na issue #23."
    ),
)
def listar(
    filtros: Annotated[FiltrosCatalogo, Query()],
    caso: ListarAtividadesCatalogo = Depends(get_listar_catalogo),
):
    resultado = caso.execute(**filtros.model_dump())
    return PaginaAtividadesResponse(
        itens=[AtividadeCatalogoResponse.model_validate(a) for a in resultado.itens],
        pagina=resultado.pagina,
        tamanho_pagina=resultado.tamanho_pagina,
        tem_proxima=resultado.tem_proxima,
    )


@router.get(
    "/{atividade_id}",
    response_model=AtividadeCatalogoResponse,
    summary="Consulta o detalhe público de uma atividade",
    description=(
        "Retorna apenas dados reutilizáveis do catálogo, sem planejamento privado. "
        "Nesta versão avaliacoes_disponiveis=false, médias e totais nulos, reviews vazios."
    ),
    responses={404: {"description": "Atividade não encontrada no catálogo"}},
)
def consultar(
    atividade_id: Annotated[int, Path(ge=1)],
    caso: ConsultarAtividadeCatalogo = Depends(get_consultar_atividade_catalogo),
):
    return AtividadeCatalogoResponse.model_validate(caso.execute(atividade_id))
