from sqlalchemy.orm import Session

from app.domain.ports.unit_of_work import UnitOfWork


class SQLAlchemyUnitOfWork(UnitOfWork):
    """Controla a transacao da Session compartilhada com os repositorios da requisicao."""

    def __init__(self, db: Session):
        self.db = db

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
