from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.avaliacao_model import AvaliacaoModel
from app.adapters.outbound.persistence.catalogo_model import (
    CatalogoAtividadeModel,
    DestinoCatalogoModel,
)
from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.domain.ports.avaliacoes_destino_repository import AvaliacoesDestinoRepository
from app.domain.ranking_destinos import AvaliacoesDestino


class SQLAlchemyAvaliacoesDestinoRepository(AvaliacoesDestinoRepository):
    def __init__(self, db: Session):
        self.db = db

    def agregar_por_destino(self) -> list[AvaliacoesDestino]:
        agregado = (
            select(
                CatalogoAtividadeModel.destino_catalogo_id.label("destino_id"),
                func.count(AvaliacaoModel.id).label("total"),
                func.sum(AvaliacaoModel.nota).label("soma"),
            )
            .join(
                CatalogoAtividadeModel,
                AvaliacaoModel.catalogo_atividade_id == CatalogoAtividadeModel.id,
            )
            .group_by(CatalogoAtividadeModel.destino_catalogo_id)
            .subquery()
        )
        resultados = self.db.execute(
            select(DestinoCatalogoModel, agregado.c.total, agregado.c.soma).join(
                agregado, agregado.c.destino_id == DestinoCatalogoModel.id
            )
        )
        return [
            AvaliacoesDestino(
                destino=SQLAlchemyCatalogoRepository._destino(destino),
                total_avaliacoes=total,
                soma_notas=int(soma),
            )
            for destino, total, soma in resultados
        ]
