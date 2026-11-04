from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.catalogo_model import CatalogoAtividadeModel
from app.adapters.outbound.persistence.roteiro_model import AtividadeViagemModel, DestinoViagemModel
from app.adapters.outbound.persistence.viagem_model import OrcamentoModel
from app.domain.entities.orcamento import Orcamento
from app.domain.enums import CategoriaAtividade, StatusAtividade
from app.domain.ports.orcamento_repository import OrcamentoRepository


class SQLAlchemyOrcamentoRepository(OrcamentoRepository):
    def __init__(self, db: Session):
        self.db = db

    def buscar(self, viagem_id: int) -> Orcamento | None:
        limite = self.db.scalar(
            select(OrcamentoModel.limite_total).where(OrcamentoModel.viagem_id == viagem_id)
        )
        # Linha com limite nulo equivale a orçamento ainda não definido.
        return Orcamento(viagem_id=viagem_id, valor_total=limite) if limite is not None else None

    def salvar(self, orcamento: Orcamento) -> Orcamento:
        # Upsert pela unicidade de viagem_id: mantém um único orçamento por viagem.
        comando = insert(OrcamentoModel).values(
            viagem_id=orcamento.viagem_id, limite_total=orcamento.valor_total
        )
        self.db.execute(
            comando.on_conflict_do_update(
                index_elements=[OrcamentoModel.viagem_id],
                set_={"limite_total": comando.excluded.limite_total, "atualizado_em": func.now()},
            )
        )
        self.db.flush()
        return orcamento

    def custos_por_categoria(self, viagem_id: int) -> dict[CategoriaAtividade, Decimal]:
        resultados = self.db.execute(
            select(CatalogoAtividadeModel.categoria, func.sum(AtividadeViagemModel.custo_previsto))
            .join(
                DestinoViagemModel, AtividadeViagemModel.destino_viagem_id == DestinoViagemModel.id
            )
            .join(
                CatalogoAtividadeModel,
                AtividadeViagemModel.catalogo_atividade_id == CatalogoAtividadeModel.id,
            )
            .where(
                DestinoViagemModel.viagem_id == viagem_id,
                AtividadeViagemModel.status != StatusAtividade.CANCELADA.value,
            )
            .group_by(CatalogoAtividadeModel.categoria)
        )
        return {CategoriaAtividade(categoria): total for categoria, total in resultados}
