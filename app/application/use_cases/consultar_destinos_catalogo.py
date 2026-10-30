from dataclasses import dataclass

from app.domain.entities.catalogo import DestinoCatalogo, texto, validar_pais_codigo
from app.domain.enums import CategoriaDestino
from app.domain.errors import DadosInvalidos, DestinoCatalogoNaoEncontrado
from app.domain.ports.catalogo_repository import CatalogoRepository


@dataclass(frozen=True)
class PaginaDestinos:
    itens: list[DestinoCatalogo]
    pagina: int
    tamanho_pagina: int
    tem_proxima: bool


class ConsultarDestinoCatalogo:
    def __init__(self, repository: CatalogoRepository):
        self.repository = repository

    def execute(self, destino_id: int) -> DestinoCatalogo:
        destino = self.repository.buscar_destino(destino_id)
        if destino is None:
            raise DestinoCatalogoNaoEncontrado("Destino não encontrado no catálogo")
        return destino


class ListarDestinosCatalogo:
    def __init__(self, repository: CatalogoRepository):
        self.repository = repository

    def execute(
        self,
        nome: str | None = None,
        pais_codigo: str | None = None,
        categoria: CategoriaDestino | None = None,
        pagina: int = 1,
        tamanho_pagina: int = 20,
    ) -> PaginaDestinos:
        if type(pagina) is not int or pagina < 1:
            raise DadosInvalidos("Página deve ser um inteiro positivo")
        if type(tamanho_pagina) is not int or not 1 <= tamanho_pagina <= 100:
            raise DadosInvalidos("Tamanho da página deve estar entre 1 e 100")
        if pais_codigo is not None:
            pais_codigo = texto(pais_codigo, "País", 2, True).upper()
            validar_pais_codigo(pais_codigo)
        if categoria is not None:
            try:
                categoria = CategoriaDestino(categoria)
            except (ValueError, TypeError) as error:
                raise DadosInvalidos("Categoria de destino inválida") from error
        itens = self.repository.listar_destinos(
            texto(nome, "Busca por nome", 255),
            pais_codigo,
            categoria,
            tamanho_pagina + 1,
            (pagina - 1) * tamanho_pagina,
        )
        return PaginaDestinos(
            itens[:tamanho_pagina], pagina, tamanho_pagina, len(itens) > tamanho_pagina
        )
