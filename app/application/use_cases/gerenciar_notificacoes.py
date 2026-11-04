from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.entities.notificacao import Notificacao
from app.domain.errors import DadosInvalidos, NotificacaoNaoEncontrada
from app.domain.ports.notificacao_repository import NotificacaoRepository
from app.domain.ports.unit_of_work import UnitOfWork


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class PaginaNotificacoes:
    itens: list[Notificacao]
    pagina: int
    tamanho_pagina: int
    tem_proxima: bool
    nao_lidas: int


class GerenciarNotificacoes:
    """Caixa de notificações do usuário autenticado (RF21).

    Toda operação recebe o id do usuário logado e só enxerga as notificações dele;
    a de outra pessoa responde como inexistente, para não revelar ids alheios.
    """

    def __init__(
        self,
        repository: NotificacaoRepository,
        uow: UnitOfWork,
        agora: Callable[[], datetime] = _agora_utc,
    ):
        self.repository = repository
        self.uow = uow
        self.agora = agora

    def listar(
        self,
        usuario_id: int,
        somente_nao_lidas: bool = False,
        pagina: int = 1,
        tamanho_pagina: int = 20,
    ) -> PaginaNotificacoes:
        if type(pagina) is not int or pagina < 1:
            raise DadosInvalidos("Página deve ser um inteiro maior ou igual a 1")
        if type(tamanho_pagina) is not int or not 1 <= tamanho_pagina <= 100:
            raise DadosInvalidos("Tamanho da página deve ser um inteiro entre 1 e 100")

        itens = self.repository.listar_do_usuario(
            usuario_id,
            somente_nao_lidas,
            limite=tamanho_pagina + 1,
            deslocamento=(pagina - 1) * tamanho_pagina,
        )
        return PaginaNotificacoes(
            itens=itens[:tamanho_pagina],
            pagina=pagina,
            tamanho_pagina=tamanho_pagina,
            tem_proxima=len(itens) > tamanho_pagina,
            nao_lidas=self.repository.contar_nao_lidas(usuario_id),
        )

    def contar_nao_lidas(self, usuario_id: int) -> int:
        return self.repository.contar_nao_lidas(usuario_id)

    def marcar_lida(self, usuario_id: int, notificacao_id: int) -> Notificacao:
        with self.uow:
            notificacao = self.repository.marcar_lida(usuario_id, notificacao_id, self.agora())
            if notificacao is None:
                raise NotificacaoNaoEncontrada("Notificação não encontrada")
            self.uow.commit()
        return notificacao

    def marcar_todas_lidas(self, usuario_id: int) -> int:
        with self.uow:
            marcadas = self.repository.marcar_todas_lidas(usuario_id, self.agora())
            self.uow.commit()
        return marcadas
