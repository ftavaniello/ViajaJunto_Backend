from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.catalogo_model import (
    CatalogoAtividadeModel,
    DestinoCatalogoModel,
)
from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.adapters.outbound.persistence.roteiro_model import AtividadeViagemModel, DestinoViagemModel
from app.domain.entities.atividade_viagem import AtividadeViagem
from app.domain.ports.atividade_viagem_repository import AtividadeViagemRepository


class SQLAlchemyAtividadeViagemRepository(AtividadeViagemRepository):
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _consulta():
        return (
            select(
                AtividadeViagemModel,
                DestinoViagemModel.viagem_id,
                CatalogoAtividadeModel,
                DestinoCatalogoModel,
            )
            .join(
                DestinoViagemModel, AtividadeViagemModel.destino_viagem_id == DestinoViagemModel.id
            )
            .join(
                CatalogoAtividadeModel,
                AtividadeViagemModel.catalogo_atividade_id == CatalogoAtividadeModel.id,
            )
            .join(
                DestinoCatalogoModel,
                CatalogoAtividadeModel.destino_catalogo_id == DestinoCatalogoModel.id,
            )
        )

    def listar(self, viagem_id: int, destino_id: int) -> list[AtividadeViagem]:
        resultados = self.db.execute(
            self._consulta()
            .where(
                DestinoViagemModel.viagem_id == viagem_id,
                AtividadeViagemModel.destino_viagem_id == destino_id,
            )
            .order_by(
                AtividadeViagemModel.data,
                AtividadeViagemModel.hora_inicio.asc().nulls_last(),
                AtividadeViagemModel.id,
            )
        )
        return [self._entidade(*linha) for linha in resultados]

    def buscar(self, viagem_id: int, destino_id: int, atividade_id: int) -> AtividadeViagem | None:
        linha = self.db.execute(
            self._consulta().where(
                DestinoViagemModel.viagem_id == viagem_id,
                AtividadeViagemModel.destino_viagem_id == destino_id,
                AtividadeViagemModel.id == atividade_id,
            )
        ).first()
        return self._entidade(*linha) if linha else None

    def salvar(self, atividade: AtividadeViagem) -> AtividadeViagem:
        if atividade.id is None:
            model = AtividadeViagemModel(
                destino_viagem_id=atividade.destino_viagem_id,
                catalogo_atividade_id=atividade.atividade.id,
            )
            self.db.add(model)
        else:
            model = self.db.get(AtividadeViagemModel, atividade.id)
        for campo in (
            "data",
            "hora_inicio",
            "duracao_minutos",
            "custo_previsto",
            "status",
            "realizada_em",
            "realizada_por_id",
        ):
            setattr(model, campo, getattr(atividade, campo))
        self.db.flush()
        salva = self.buscar(atividade.viagem_id, atividade.destino_viagem_id, model.id)
        if salva is None:
            raise RuntimeError("Atividade gravada não encontrada no contexto do roteiro")
        return salva

    def deletar(self, atividade: AtividadeViagem) -> None:
        self.db.delete(self.db.get(AtividadeViagemModel, atividade.id))
        self.db.flush()

    @staticmethod
    def _entidade(
        model: AtividadeViagemModel,
        viagem_id: int,
        catalogo: CatalogoAtividadeModel,
        destino: DestinoCatalogoModel,
    ) -> AtividadeViagem:
        dados_destino = SQLAlchemyCatalogoRepository._destino(destino)
        dados_catalogo = SQLAlchemyCatalogoRepository._atividade(catalogo, dados_destino)
        return AtividadeViagem(
            id=model.id,
            viagem_id=viagem_id,
            destino_viagem_id=model.destino_viagem_id,
            atividade=dados_catalogo,
            data=model.data,
            hora_inicio=model.hora_inicio,
            duracao_minutos=model.duracao_minutos,
            custo_previsto=model.custo_previsto,
            status=model.status,
            realizada_em=model.realizada_em,
            realizada_por_id=model.realizada_por_id,
        )
