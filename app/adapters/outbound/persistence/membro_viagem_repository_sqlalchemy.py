from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.viagem_model import MembroViagemModel
from app.domain.enums import PapelMembro
from app.domain.ports.membro_viagem_repository import MembroViagemRepository


class SQLAlchemyMembroViagemRepository(MembroViagemRepository):
    def __init__(self, db: Session):
        self.db = db

    def buscar_papel(self, viagem_id: int, usuario_id: int) -> PapelMembro | None:
        papel = self.db.scalar(
            select(MembroViagemModel.papel).where(
                MembroViagemModel.viagem_id == viagem_id,
                MembroViagemModel.usuario_id == usuario_id,
            )
        )
        return PapelMembro(papel) if papel is not None else None
