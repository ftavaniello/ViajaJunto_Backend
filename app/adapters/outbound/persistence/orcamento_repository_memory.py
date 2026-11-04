from decimal import Decimal

from app.adapters.outbound.persistence.atividade_viagem_repository_memory import (
    AtividadeViagemRepositoryMemory,
)
from app.domain.entities.orcamento import Orcamento
from app.domain.enums import CategoriaAtividade, StatusAtividade
from app.domain.ports.orcamento_repository import OrcamentoRepository


class OrcamentoRepositoryMemory(OrcamentoRepository):
    def __init__(self, atividades: AtividadeViagemRepositoryMemory | None = None):
        self.orcamentos: dict[int, Orcamento] = {}
        # Faz o papel do JOIN com atividades_viagem do banco.
        self.atividades = atividades or AtividadeViagemRepositoryMemory()

    def buscar(self, viagem_id: int) -> Orcamento | None:
        return self.orcamentos.get(viagem_id)

    def salvar(self, orcamento: Orcamento) -> Orcamento:
        self.orcamentos[orcamento.viagem_id] = orcamento
        return orcamento

    def custos_por_categoria(self, viagem_id: int) -> dict[CategoriaAtividade, Decimal]:
        custos: dict[CategoriaAtividade, Decimal] = {}
        for atividade in self.atividades.atividades.values():
            if atividade.viagem_id != viagem_id or atividade.status == StatusAtividade.CANCELADA:
                continue
            categoria = atividade.atividade.categoria
            custos[categoria] = custos.get(categoria, Decimal("0")) + atividade.custo_previsto
        return custos
