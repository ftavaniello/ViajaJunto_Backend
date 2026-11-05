from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.adapters.outbound.persistence.viagem_model import MembroViagemModel, ViagemModel
from app.domain.ports.vinculos_conta_repository import VinculosContaRepository


class SQLAlchemyVinculosContaRepository(VinculosContaRepository):
    def __init__(self, db: Session):
        self.db = db

    def bloquear_e_verificar_colaboradores(self, usuario_id: int) -> bool:
        # FOR UPDATE conflita com o KEY SHARE das FKs: novas viagens do usuário
        # aguardam o término da exclusão, inclusive quando ele ainda não tem viagens.
        self.db.execute(
            select(UsuarioModel.id).where(UsuarioModel.id == usuario_id).with_for_update()
        ).all()
        # Mesma proteção para novos membros; ordem fixa reduz risco de deadlock.
        # Consulta separada de membros garante snapshot posterior à espera pelo lock.
        self.db.execute(
            select(ViagemModel.id)
            .where(ViagemModel.criador_id == usuario_id)
            .order_by(ViagemModel.id)
            .with_for_update()
        ).all()
        return self.db.scalar(
            select(
                select(MembroViagemModel.id)
                .join(ViagemModel, ViagemModel.id == MembroViagemModel.viagem_id)
                .where(
                    ViagemModel.criador_id == usuario_id,
                    MembroViagemModel.usuario_id != usuario_id,
                )
                .exists()
            )
        )
