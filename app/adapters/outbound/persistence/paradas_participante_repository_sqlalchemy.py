from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.catalogo_model import DestinoCatalogoModel
from app.adapters.outbound.persistence.roteiro_model import DestinoViagemModel
from app.adapters.outbound.persistence.viagem_model import MembroViagemModel, ViagemModel
from app.domain.enums import StatusViagem
from app.domain.paises_visitados import ParadaDoParticipante
from app.domain.ports.paradas_participante_repository import ParadasParticipanteRepository


class SQLAlchemyParadasParticipanteRepository(ParadasParticipanteRepository):
    def __init__(self, db: Session):
        self.db = db

    def listar(self, usuario_id: int) -> list[ParadaDoParticipante]:
        # O vínculo único por (viagem, usuário) impede duplicação no JOIN com membros.
        resultados = self.db.execute(
            select(
                DestinoViagemModel.viagem_id,
                ViagemModel.status,
                DestinoCatalogoModel.pais_codigo,
                DestinoViagemModel.data_chegada,
            )
            .join(ViagemModel, DestinoViagemModel.viagem_id == ViagemModel.id)
            .join(
                DestinoCatalogoModel,
                DestinoViagemModel.destino_catalogo_id == DestinoCatalogoModel.id,
            )
            .outerjoin(MembroViagemModel, and_(
                MembroViagemModel.viagem_id == ViagemModel.id,
                MembroViagemModel.usuario_id == usuario_id,
            ))
            .where(or_(ViagemModel.criador_id == usuario_id, MembroViagemModel.id.is_not(None)))
        )
        return [
            ParadaDoParticipante(
                viagem_id=viagem_id,
                status_viagem=StatusViagem(status),
                pais_codigo=pais_codigo,
                data_chegada=data_chegada,
            )
            for viagem_id, status, pais_codigo, data_chegada in resultados
        ]
