from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.viagem_model import (
    MEMBROS_VIAGEM_UNIQUE,
    MembroViagemModel,
)
from app.domain.enums import PapelMembro
from app.domain.errors import MembroJaParticipa
from app.domain.membro_viagem import MembroViagem
from app.domain.ports.membro_viagem_repository import MembroViagemRepository


class SQLAlchemyMembroViagemRepository(MembroViagemRepository):
    """Grava na transacao corrente da Session; quem confirma ou desfaz e a UnitOfWork."""

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

    def adicionar(self, viagem_id: int, usuario_id: int, papel: PapelMembro) -> None:
        self.db.add(
            MembroViagemModel(viagem_id=viagem_id, usuario_id=usuario_id, papel=papel.value)
        )
        try:
            self.db.flush()
        except IntegrityError as error:
            # Duas aceitacoes simultaneas passam pela checagem previa do caso de uso;
            # quem garante o vinculo unico e a constraint do banco.
            diag = getattr(error.orig, "diag", None)
            if getattr(diag, "constraint_name", None) == MEMBROS_VIAGEM_UNIQUE:
                raise MembroJaParticipa("Você já participa desta viagem") from error
            raise

    def alterar_papel(self, viagem_id: int, usuario_id: int, papel: PapelMembro) -> None:
        self.db.execute(
            update(MembroViagemModel)
            .where(
                MembroViagemModel.viagem_id == viagem_id,
                MembroViagemModel.usuario_id == usuario_id,
            )
            .values(papel=papel.value)
        )

    def remover(self, viagem_id: int, usuario_id: int) -> None:
        self.db.execute(
            delete(MembroViagemModel).where(
                MembroViagemModel.viagem_id == viagem_id,
                MembroViagemModel.usuario_id == usuario_id,
            )
        )

    def listar(self, viagem_id: int) -> list[MembroViagem]:
        modelos = self.db.scalars(
            select(MembroViagemModel)
            .where(MembroViagemModel.viagem_id == viagem_id)
            .order_by(MembroViagemModel.entrou_em, MembroViagemModel.id)
        )
        return [MembroViagem(m.usuario_id, PapelMembro(m.papel), m.entrou_em) for m in modelos]
