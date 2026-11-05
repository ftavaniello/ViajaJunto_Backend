from app.application.acesso_viagem import PoliticaAcessoViagem
from app.application.notificador_viagem import NotificadorViagem
from app.domain.enums import TipoNotificacao
from app.domain.permissoes import AcaoViagem
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.viagem_repository import ViagemRepository


class ExcluirViagem:
    def __init__(self, repository: ViagemRepository, acesso: PoliticaAcessoViagem,
                 uow: UnitOfWork, notificador: NotificadorViagem | None = None):
        self.repository = repository
        self.acesso = acesso
        self.uow = uow
        self.notificador = notificador

    def execute(self, viagem_id: int, usuario_id: int) -> None:
        viagem = self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.EXCLUIR)

        with self.uow:
            # Avisa antes de excluir, enquanto os colaboradores ainda estao na viagem.
            # As notificacoes sobrevivem com viagem_id nulo (ON DELETE SET NULL).
            if self.notificador is not None:
                self.notificador.notificar(
                    viagem,
                    TipoNotificacao.VIAGEM_EXCLUIDA,
                    usuario_id,
                    f'excluiu a viagem "{viagem.nome}" '
                    f"({viagem.data_inicio:%d/%m/%Y} a {viagem.data_fim:%d/%m/%Y}).",
                )
            self.repository.deletar(viagem_id)
            self.uow.commit()
