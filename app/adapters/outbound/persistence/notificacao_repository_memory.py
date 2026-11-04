from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.domain.entities.notificacao import Notificacao
from app.domain.ports.notificacao_repository import NotificacaoRepository

_INICIO = datetime(2026, 1, 1, tzinfo=timezone.utc)


class NotificacaoRepositoryMemory(NotificacaoRepository):
    def __init__(self):
        self.notificacoes: dict[int, Notificacao] = {}
        self.proximo_id = 1

    def adicionar(self, notificacoes: list[Notificacao]) -> None:
        for notificacao in notificacoes:
            # criado_em crescente por id faz o papel do server_default do banco.
            self.notificacoes[self.proximo_id] = replace(
                notificacao,
                id=self.proximo_id,
                criado_em=_INICIO + timedelta(seconds=self.proximo_id),
            )
            self.proximo_id += 1

    def listar_do_usuario(
        self, usuario_id: int, somente_nao_lidas: bool, limite: int, deslocamento: int
    ) -> list[Notificacao]:
        do_usuario = [
            n
            for n in self.notificacoes.values()
            if n.usuario_id == usuario_id and not (somente_nao_lidas and n.lida)
        ]
        do_usuario.sort(key=lambda n: (n.lida, -n.criado_em.timestamp(), -n.id))
        return [replace(n) for n in do_usuario[deslocamento : deslocamento + limite]]

    def contar_nao_lidas(self, usuario_id: int) -> int:
        return sum(
            1 for n in self.notificacoes.values() if n.usuario_id == usuario_id and not n.lida
        )

    def marcar_lida(
        self, usuario_id: int, notificacao_id: int, agora: datetime
    ) -> Notificacao | None:
        notificacao = self.notificacoes.get(notificacao_id)
        if notificacao is None or notificacao.usuario_id != usuario_id:
            return None
        if not notificacao.lida:
            notificacao.lida_em = agora
        return replace(notificacao)

    def marcar_todas_lidas(self, usuario_id: int, agora: datetime) -> int:
        marcadas = 0
        for notificacao in self.notificacoes.values():
            if notificacao.usuario_id == usuario_id and not notificacao.lida:
                notificacao.lida_em = agora
                marcadas += 1
        return marcadas

    def do_usuario(self, usuario_id: int) -> list[Notificacao]:
        """Atalho dos testes: todas as notificacoes do usuario, em ordem de criacao."""
        return [n for n in self.notificacoes.values() if n.usuario_id == usuario_id]
