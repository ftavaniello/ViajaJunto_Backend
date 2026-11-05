from dataclasses import dataclass

from app.domain.entities.viagem import Viagem
from app.domain.errors import DadosInvalidos
from app.domain.permissoes import PerfilViagem, perfil_na_viagem
from app.domain.ports.viagem_repository import ViagemRepository


@dataclass(frozen=True)
class ItemListaViagens:
    viagem: Viagem
    papel_usuario: PerfilViagem


@dataclass(frozen=True)
class PaginaViagens:
    itens: list[ItemListaViagens]
    pagina: int
    tamanho_pagina: int
    tem_proxima: bool


class ListarViagens:
    def __init__(self, repository: ViagemRepository):
        self.repository = repository

    def execute(
        self, usuario_id: int, pagina: int = 1, tamanho_pagina: int = 20
    ) -> PaginaViagens:
        if type(pagina) is not int or pagina < 1:
            raise DadosInvalidos("Página deve ser um inteiro maior ou igual a 1")
        if type(tamanho_pagina) is not int or not 1 <= tamanho_pagina <= 100:
            raise DadosInvalidos("Tamanho da página deve ser um inteiro entre 1 e 100")

        participacoes = self.repository.listar_por_participante(
            usuario_id, limite=tamanho_pagina + 1,
            deslocamento=(pagina - 1) * tamanho_pagina,
        )
        itens = []
        for participacao in participacoes[:tamanho_pagina]:
            viagem = participacao.viagem
            perfil = perfil_na_viagem(viagem.criador_id, usuario_id, participacao.papel_membro)
            if perfil is not None:
                itens.append(ItemListaViagens(viagem, perfil))
        return PaginaViagens(itens, pagina, tamanho_pagina, len(participacoes) > tamanho_pagina)
