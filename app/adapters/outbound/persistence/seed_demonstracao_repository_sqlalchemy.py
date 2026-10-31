from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.adapters.outbound.persistence.viagem_model import MembroViagemModel
from app.domain.enums import PapelMembro
from app.infrastructure.database import Base


class SeedDemonstracaoModel(Base):
    __tablename__ = "seeds_demonstracao"

    chave: Mapped[str] = mapped_column(String(80), primary_key=True)
    manifesto: Mapped[dict] = mapped_column(JSON, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SQLAlchemySeedDemonstracaoRepository:
    def __init__(self, db: Session):
        self.db = db

    def reservar(self, chave: str) -> dict | None:
        # Lock da transação externa: sobrevive aos savepoints dos casos de uso.
        self.db.execute(select(func.pg_advisory_xact_lock(202647, 1)))
        model = self.db.get(SeedDemonstracaoModel, chave)
        return model.manifesto if model is not None else None

    def vincular(self, viagem_id: int, usuario_id: int, papel: PapelMembro) -> None:
        self.db.add(
            MembroViagemModel(viagem_id=viagem_id, usuario_id=usuario_id, papel=papel.value)
        )
        self.db.flush()

    def concluir(self, chave: str, manifesto: dict) -> None:
        self.db.add(SeedDemonstracaoModel(chave=chave, manifesto=manifesto))
        self.db.flush()
