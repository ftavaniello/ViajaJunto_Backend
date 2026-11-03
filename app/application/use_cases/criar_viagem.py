from datetime import date

from app.domain.entities.viagem import Viagem
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.viagem_repository import ViagemRepository


class CriarViagem:
    def __init__(self, repository: ViagemRepository, uow: UnitOfWork):
        self.repository = repository
        self.uow = uow

    def execute(self, criador_id: int, nome: str, descricao: str | None,
                data_inicio: date, data_fim: date) -> Viagem:
        # criador_id vem da identidade autenticada, nunca do corpo da requisicao.
        viagem = Viagem(
            criador_id=criador_id,
            nome=nome,
            descricao=descricao,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

        with self.uow:
            salva = self.repository.salvar(viagem)
            self.uow.commit()

        return salva
