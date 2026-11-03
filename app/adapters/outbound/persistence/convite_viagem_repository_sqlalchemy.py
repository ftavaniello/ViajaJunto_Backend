from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.convite_viagem_model import ConviteViagemModel
from app.domain.entities.convite_viagem import ConviteViagem
from app.domain.ports.convite_viagem_repository import ConviteViagemRepository


class SQLAlchemyConviteViagemRepository(ConviteViagemRepository):
    """Grava na transacao corrente da Session; quem confirma ou desfaz e a UnitOfWork."""

    def __init__(self, db: Session):
        self.db = db

    def salvar(self, convite: ConviteViagem) -> ConviteViagem:
        if convite.id is None:
            model = ConviteViagemModel(
                viagem_id=convite.viagem_id,
                email=convite.email,
                token_hash=convite.token_hash,
                convidado_por_id=convite.convidado_por_id,
                expira_em=convite.expira_em,
            )
            self.db.add(model)
        else:
            # Depois de emitido, so o aceite muda.
            model = self.db.get(ConviteViagemModel, convite.id)
        model.aceito_em = convite.aceito_em

        self.db.flush()
        self.db.refresh(model)

        return self._to_entity(model)

    def buscar_por_hash(self, token_hash: str) -> ConviteViagem | None:
        model = self.db.scalar(
            select(ConviteViagemModel).where(ConviteViagemModel.token_hash == token_hash)
        )
        return self._to_entity(model) if model else None

    def buscar(self, viagem_id: int, convite_id: int) -> ConviteViagem | None:
        model = self.db.get(ConviteViagemModel, convite_id)
        if model is None or model.viagem_id != viagem_id:
            return None
        return self._to_entity(model)

    def listar_pendentes(self, viagem_id: int, agora: datetime) -> list[ConviteViagem]:
        modelos = self.db.scalars(
            select(ConviteViagemModel)
            .where(
                ConviteViagemModel.viagem_id == viagem_id,
                ConviteViagemModel.aceito_em.is_(None),
                ConviteViagemModel.expira_em > agora,
            )
            .order_by(ConviteViagemModel.criado_em, ConviteViagemModel.id)
        )
        return [self._to_entity(m) for m in modelos]

    def remover(self, convite_id: int) -> None:
        self.db.execute(delete(ConviteViagemModel).where(ConviteViagemModel.id == convite_id))

    def remover_pendentes(self, viagem_id: int, email: str) -> None:
        self.db.execute(
            delete(ConviteViagemModel).where(
                ConviteViagemModel.viagem_id == viagem_id,
                ConviteViagemModel.email == email,
                ConviteViagemModel.aceito_em.is_(None),
            )
        )

    @staticmethod
    def _to_entity(model: ConviteViagemModel) -> ConviteViagem:
        return ConviteViagem(
            id=model.id,
            viagem_id=model.viagem_id,
            email=model.email,
            token_hash=model.token_hash,
            convidado_por_id=model.convidado_por_id,
            expira_em=model.expira_em,
            aceito_em=model.aceito_em,
            criado_em=model.criado_em,
        )
