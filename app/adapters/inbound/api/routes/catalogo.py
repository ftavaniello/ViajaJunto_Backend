from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.adapters.inbound.api.schemas.avaliacao_schema import FiltrosAvaliacoes
from app.adapters.inbound.api.schemas.catalogo_schema import (
    AtividadeCatalogoResponse,
    FiltrosCatalogo,
    PaginaAtividadesResponse,
    PaginaAvaliacoesResponse,
    ReviewCatalogoResponse,
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
        "Médias calculadas de todas as avaliações, incluindo autores excluídos. "
        "Nota mínima inclusiva, sem arredondar antes de filtrar. A listagem traz "
        "resumos; reviews paginados estão no detalhe e na rota /avaliacoes."
    ),
)
def listar(
    filtros: Annotated[FiltrosCatalogo, Query()],
    caso: Annotated[ListarAtividadesCatalogo, Depends(get_listar_catalogo)],
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
        "Inclui média, total e até 20 reviews mais recentes. Sem avaliações: média nula, "
        "total zero e reviews vazios. Todos os reviews estão disponíveis pela rota /avaliacoes."
    ),
    responses={404: {"description": "Atividade não encontrada no catálogo"}},
)
def consultar(
    atividade_id: Annotated[int, Path(ge=1)],
    caso: Annotated[ConsultarAtividadeCatalogo, Depends(get_consultar_atividade_catalogo)],
):
    resultado = caso.execute(atividade_id)
    return AtividadeCatalogoResponse.model_validate(resultado.atividade).model_copy(
        update={
            "reviews": [ReviewCatalogoResponse.model_validate(r) for r in resultado.reviews],
        }
    )


@router.get(
    "/{atividade_id}/avaliacoes",
    response_model=PaginaAvaliacoesResponse,
    summary="Lista avaliações públicas de uma atividade",
    description="Sem autenticação. Ordem por data de criação e ID decrescentes; "
    "nomes de contas excluídas aparecem como nulos. Não expõe email nem dados de viagem.",
    responses={404: {"description": "Atividade não encontrada no catálogo"}},
)
def listar_avaliacoes(
    atividade_id: Annotated[int, Path(ge=1)],
    filtros: Annotated[FiltrosAvaliacoes, Query()],
    caso: Annotated[ConsultarAtividadeCatalogo, Depends(get_consultar_atividade_catalogo)],
):
    resultado = caso.listar_avaliacoes(atividade_id, **filtros.model_dump())
    return PaginaAvaliacoesResponse(
        itens=[ReviewCatalogoResponse.model_validate(r) for r in resultado.itens],
        pagina=resultado.pagina,
        tamanho_pagina=resultado.tamanho_pagina,
        tem_proxima=resultado.tem_proxima,
    )
