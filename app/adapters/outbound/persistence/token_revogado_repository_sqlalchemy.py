from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.token_revogado_model import TokenRevogadoModel
from app.domain.ports.token_revogado_repository import TokenRevogadoRepository


class SQLAlchemyTokenRevogadoRepository(TokenRevogadoRepository):
    """Grava na transacao corrente da Session; quem confirma ou desfaz e a UnitOfWork."""

    def __init__(self, db: Session):
        self.db = db

    def revogar(self, jti: str, usuario_id: int, expira_em: datetime) -> None:
        # Limpeza oportunista: revogacoes de tokens ja expirados nao protegem mais nada.
        self.db.execute(
            delete(TokenRevogadoModel).where(
                TokenRevogadoModel.expira_em < datetime.now(timezone.utc)
            )
        )
        if self.db.get(TokenRevogadoModel, jti) is None:
            self.db.add(TokenRevogadoModel(jti=jti, usuario_id=usuario_id, expira_em=expira_em))
        self.db.flush()

    def esta_revogado(self, jti: str) -> bool:
        return self.db.scalar(
            select(TokenRevogadoModel.jti).where(TokenRevogadoModel.jti == jti)
        ) is not None
