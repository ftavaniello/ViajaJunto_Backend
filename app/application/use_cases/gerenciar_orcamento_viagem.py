from decimal import Decimal

from app.application.acesso_viagem import PoliticaAcessoViagem
from app.domain.entities.orcamento import Orcamento, ResumoFinanceiro
from app.domain.permissoes import AcaoViagem
from app.domain.ports.orcamento_repository import OrcamentoRepository
from app.domain.ports.unit_of_work import UnitOfWork


class GerenciarOrcamentoViagem:
    """Orçamento único por viagem (RF15) e resumo financeiro (RF17).

    Os custos previstos (RF16) ficam nas atividades do roteiro; o resumo os soma a
    cada consulta, então incluir, editar ou remover atividades reflete imediatamente.
    """

    def __init__(
        self, repository: OrcamentoRepository, acesso: PoliticaAcessoViagem, uow: UnitOfWork
    ):
        self.repository = repository
        self.acesso = acesso
        self.uow = uow

    def _resumo(self, viagem_id: int) -> ResumoFinanceiro:
        return ResumoFinanceiro.calcular(
            viagem_id,
            self.repository.buscar(viagem_id),
            self.repository.custos_por_categoria(viagem_id),
        )

    def consultar_resumo(self, viagem_id: int, usuario_id: int) -> ResumoFinanceiro:
        self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.CONSULTAR)
        return self._resumo(viagem_id)

    def definir(self, viagem_id: int, usuario_id: int, valor_total: Decimal) -> ResumoFinanceiro:
        with self.uow:
            self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.EDITAR)
            self.repository.salvar(Orcamento(viagem_id=viagem_id, valor_total=valor_total))
            resumo = self._resumo(viagem_id)
            self.uow.commit()
        return resumo
