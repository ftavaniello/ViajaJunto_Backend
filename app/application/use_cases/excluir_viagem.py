from app.application.acesso_viagem import PoliticaAcessoViagem
from app.domain.permissoes import AcaoViagem
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.viagem_repository import ViagemRepository


class ExcluirViagem:
    def __init__(self, repository: ViagemRepository, acesso: PoliticaAcessoViagem,
                 uow: UnitOfWork):
        self.repository = repository
        self.acesso = acesso
        self.uow = uow

    def execute(self, viagem_id: int, usuario_id: int) -> None:
        self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.EXCLUIR)

        with self.uow:
            self.repository.deletar(viagem_id)
            self.uow.commit()
