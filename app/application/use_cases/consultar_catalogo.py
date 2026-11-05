from dataclasses import dataclass
from decimal import Decimal

from app.domain.entities.avaliacao import ReviewPublico
from app.domain.entities.catalogo import AtividadeCatalogo, texto
from app.domain.enums import CategoriaAtividade
from app.domain.errors import AtividadeCatalogoNaoEncontrada, DadosInvalidos
from app.domain.ports.avaliacao_repository import AvaliacaoRepository
from app.domain.ports.catalogo_repository import CatalogoRepository


@dataclass(frozen=True)
class PaginaAtividades:
    itens: list[AtividadeCatalogo]
    pagina: int
    tamanho_pagina: int
    tem_proxima: bool


@dataclass(frozen=True)
class DetalheAtividadeCatalogo:
    atividade: AtividadeCatalogo
    reviews: list[ReviewPublico]


@dataclass(frozen=True)
class PaginaAvaliacoes:
    itens: list[ReviewPublico]
    pagina: int
    tamanho_pagina: int
    tem_proxima: bool


def validar_paginacao(pagina: int, tamanho_pagina: int) -> None:
    if type(pagina) is not int or pagina < 1:
        raise DadosInvalidos("Página deve ser um inteiro positivo")
    if type(tamanho_pagina) is not int or not 1 <= tamanho_pagina <= 100:
        raise DadosInvalidos("Tamanho da página deve estar entre 1 e 100")


class ConsultarAtividadeCatalogo:
    def __init__(self, repository: CatalogoRepository, avaliacoes: AvaliacaoRepository):
        self.repository = repository
        self.avaliacoes = avaliacoes

    def execute(self, atividade_id: int) -> DetalheAtividadeCatalogo:
        atividade = self._atividade(atividade_id)
        return DetalheAtividadeCatalogo(atividade, self.avaliacoes.listar(atividade_id, 20, 0))

    def _atividade(self, atividade_id: int) -> AtividadeCatalogo:
        atividade = self.repository.buscar_atividade(atividade_id)
        if atividade is None:
            raise AtividadeCatalogoNaoEncontrada("Atividade não encontrada no catálogo")
        return atividade

    def listar_avaliacoes(
        self,
        atividade_id: int,
        pagina: int = 1,
        tamanho_pagina: int = 20,
    ) -> PaginaAvaliacoes:
        validar_paginacao(pagina, tamanho_pagina)
        self._atividade(atividade_id)
        itens = self.avaliacoes.listar(
            atividade_id,
            tamanho_pagina + 1,
            (pagina - 1) * tamanho_pagina,
        )
        return PaginaAvaliacoes(
            itens[:tamanho_pagina],
            pagina,
            tamanho_pagina,
            len(itens) > tamanho_pagina,
        )


class ListarAtividadesCatalogo:
    def __init__(self, repository: CatalogoRepository):
        self.repository = repository

    def execute(
        self,
        nome: str | None = None,
        categoria: CategoriaAtividade | None = None,
        localizacao: str | None = None,
        destino_catalogo_id: int | None = None,
        pagina: int = 1,
        tamanho_pagina: int = 20,
        nota_minima: Decimal | None = None,
    ) -> PaginaAtividades:
        validar_paginacao(pagina, tamanho_pagina)
        if nota_minima is not None:
            if type(nota_minima) not in (int, float, Decimal):
                raise DadosInvalidos("Nota mínima deve ser um número entre 1 e 5")
            nota_minima = Decimal(str(nota_minima))
            if not nota_minima.is_finite() or not 1 <= nota_minima <= 5:
                raise DadosInvalidos("Nota mínima deve ser um número entre 1 e 5")
        if destino_catalogo_id is not None and (
            type(destino_catalogo_id) is not int or destino_catalogo_id < 1
        ):
            raise DadosInvalidos("Destino deve ter um id positivo")
        if categoria is not None:
            try:
                categoria = CategoriaAtividade(categoria)
            except (ValueError, TypeError) as error:
                raise DadosInvalidos("Categoria inválida") from error
        itens = self.repository.listar_atividades(
            texto(nome, "Busca por nome", 255),
            categoria,
            texto(localizacao, "Localização", 255),
            destino_catalogo_id,
            tamanho_pagina + 1,
            (pagina - 1) * tamanho_pagina,
            nota_minima,
        )
        return PaginaAtividades(
            itens[:tamanho_pagina], pagina, tamanho_pagina, len(itens) > tamanho_pagina
        )
