from datetime import date

from app.application.acesso_viagem import PoliticaAcessoViagem
from app.domain.entities.viagem import Viagem
from app.domain.enums import StatusViagem
from app.domain.permissoes import AcaoViagem
from app.domain.ports.destino_viagem_repository import DestinoViagemRepository
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.viagem_repository import ViagemRepository


class AtualizarViagem:
    def __init__(
        self,
        repository: ViagemRepository,
        acesso: PoliticaAcessoViagem,
        uow: UnitOfWork,
        roteiro: DestinoViagemRepository,
    ):
        self.repository = repository
        self.acesso = acesso
        self.uow = uow
        self.roteiro = roteiro

    def execute(
        self,
        viagem_id: int,
        usuario_id: int,
        nome: str | None = None,
        descricao: str | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        status: StatusViagem | None = None,
    ) -> Viagem:
        with self.uow:
            self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.EDITAR)
            self.roteiro.bloquear_roteiro(viagem_id)
            viagem = self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.EDITAR)

            # Campos None permanecem inalterados; o periodo e validado ja combinado.
            viagem_atualizada = Viagem(
                id=viagem.id,
                criador_id=viagem.criador_id,
                nome=viagem.nome if nome is None else nome,
                descricao=viagem.descricao if descricao is None else descricao,
                data_inicio=viagem.data_inicio if data_inicio is None else data_inicio,
                data_fim=viagem.data_fim if data_fim is None else data_fim,
                status=viagem.status if status is None else status,
                codigo_convite=viagem.codigo_convite,
                codigo_convite_expira_em=viagem.codigo_convite_expira_em,
                criado_em=viagem.criado_em,
            )

            for destino in self.roteiro.listar(viagem_id):
                destino.validar_periodo(viagem_atualizada.data_inicio, viagem_atualizada.data_fim)
            salva = self.repository.salvar(viagem_atualizada)
            self.uow.commit()

        return salva
