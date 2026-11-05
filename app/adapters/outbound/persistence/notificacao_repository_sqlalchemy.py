from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.notificacao_model import NotificacaoModel
from app.domain.entities.notificacao import Notificacao
from app.domain.enums import TipoNotificacao
from app.domain.ports.notificacao_repository import NotificacaoRepository


class SQLAlchemyNotificacaoRepository(NotificacaoRepository):
    """Grava na transacao corrente da Session; quem confirma ou desfaz e a UnitOfWork."""

    def __init__(self, db: Session):
        self.db = db

    def adicionar(self, notificacoes: list[Notificacao]) -> None:
        self.db.add_all(
            NotificacaoModel(
                usuario_id=n.usuario_id,
                tipo=n.tipo.value,
                viagem_id=n.viagem_id,
                ator_id=n.ator_id,
                mensagem=n.mensagem,
            )
            for n in notificacoes
        )
        # Grava ja: a exclusao da viagem que vem depois precisa encontrar as linhas
        # para aplicar o ON DELETE SET NULL.
        self.db.flush()

    def listar_do_usuario(
        self, usuario_id: int, somente_nao_lidas: bool, limite: int, deslocamento: int
    ) -> list[Notificacao]:
        consulta = select(NotificacaoModel).where(NotificacaoModel.usuario_id == usuario_id)
        if somente_nao_lidas:
            consulta = consulta.where(NotificacaoModel.lida_em.is_(None))
        modelos = self.db.scalars(
            consulta.order_by(
                NotificacaoModel.lida_em.is_not(None),
                NotificacaoModel.criado_em.desc(),
                NotificacaoModel.id.desc(),
            )
            .limit(limite)
            .offset(deslocamento)
        )
        return [self._to_entity(m) for m in modelos]

    def contar_nao_lidas(self, usuario_id: int) -> int:
        return self.db.scalar(
            select(func.count()).where(
                NotificacaoModel.usuario_id == usuario_id, NotificacaoModel.lida_em.is_(None)
            )
        )

    def marcar_lida(
        self, usuario_id: int, notificacao_id: int, agora: datetime
    ) -> Notificacao | None:
        model = self.db.get(NotificacaoModel, notificacao_id)
        if model is None or model.usuario_id != usuario_id:
            return None
        if model.lida_em is None:
            model.lida_em = agora
            self.db.flush()
        return self._to_entity(model)

    def marcar_todas_lidas(self, usuario_id: int, agora: datetime) -> int:
        resultado = self.db.execute(
            update(NotificacaoModel)
            .where(NotificacaoModel.usuario_id == usuario_id, NotificacaoModel.lida_em.is_(None))
            .values(lida_em=agora)
        )
        return resultado.rowcount

    @staticmethod
    def _to_entity(model: NotificacaoModel) -> Notificacao:
        return Notificacao(
            id=model.id,
            usuario_id=model.usuario_id,
            tipo=TipoNotificacao(model.tipo),
            viagem_id=model.viagem_id,
            ator_id=model.ator_id,
            mensagem=model.mensagem,
            lida_em=model.lida_em,
            criado_em=model.criado_em,
        )
