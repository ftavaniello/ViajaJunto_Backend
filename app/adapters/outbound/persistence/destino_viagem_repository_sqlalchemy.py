from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.catalogo_model import DestinoCatalogoModel
from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.adapters.outbound.persistence.roteiro_model import AtividadeViagemModel, DestinoViagemModel
from app.adapters.outbound.persistence.viagem_model import ViagemModel
from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.ports.destino_viagem_repository import DestinoViagemRepository


class SQLAlchemyDestinoViagemRepository(DestinoViagemRepository):
    def __init__(self, db: Session):
        self.db = db

    def bloquear_roteiro(self, viagem_id: int) -> None:
        self.db.execute(
            select(ViagemModel)
            .where(ViagemModel.id == viagem_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).all()

    def listar(self, viagem_id: int) -> list[DestinoViagem]:
        resultados = self.db.execute(
            select(DestinoViagemModel, DestinoCatalogoModel)
            .join(DestinoCatalogoModel)
            .where(DestinoViagemModel.viagem_id == viagem_id)
            .order_by(DestinoViagemModel.ordem, DestinoViagemModel.id)
        )
        return [self._entidade(model, catalogo) for model, catalogo in resultados]

    def buscar(self, viagem_id: int, destino_id: int) -> DestinoViagem | None:
        resultado = self.db.execute(
            select(DestinoViagemModel, DestinoCatalogoModel)
            .join(DestinoCatalogoModel)
            .where(DestinoViagemModel.id == destino_id, DestinoViagemModel.viagem_id == viagem_id)
        ).first()
        return self._entidade(*resultado) if resultado else None

    def salvar(self, destino: DestinoViagem) -> DestinoViagem:
        if destino.id is None:
            model = DestinoViagemModel(
                viagem_id=destino.viagem_id, destino_catalogo_id=destino.destino.id
            )
            self.db.add(model)
        else:
            model = self.db.get(DestinoViagemModel, destino.id)
        model.ordem = destino.ordem
        model.data_chegada = destino.data_chegada
        model.data_saida = destino.data_saida
        model.observacoes = destino.descricao
        model.hospedagem = destino.hospedagem
        self.db.flush()
        catalogo = self.db.get(DestinoCatalogoModel, model.destino_catalogo_id)
        return self._entidade(model, catalogo)

    def deletar(self, destino: DestinoViagem) -> None:
        model = self.db.get(DestinoViagemModel, destino.id)
        self.db.delete(model)
        self.db.flush()

    def datas_atividades(self, destino_id: int) -> list[date]:
        return list(
            self.db.scalars(
                select(AtividadeViagemModel.data).where(
                    AtividadeViagemModel.destino_viagem_id == destino_id,
                )
            )
        )

    @staticmethod
    def _entidade(model: DestinoViagemModel, catalogo: DestinoCatalogoModel) -> DestinoViagem:
        return DestinoViagem(
            id=model.id,
            viagem_id=model.viagem_id,
            destino=SQLAlchemyCatalogoRepository._destino(catalogo),
            ordem=model.ordem,
            data_chegada=model.data_chegada,
            data_saida=model.data_saida,
            descricao=model.observacoes,
            hospedagem=model.hospedagem,
        )
