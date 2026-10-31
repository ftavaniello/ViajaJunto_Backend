from collections.abc import Callable
from datetime import date, datetime, timezone

from app.domain.convite import expiracao_convite, gerar_codigo_convite
from app.domain.entities.viagem import Viagem
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.viagem_repository import ViagemRepository


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class CriarViagem:
    def __init__(self, repository: ViagemRepository, uow: UnitOfWork,
                 agora: Callable[[], datetime] = _agora_utc):
        self.repository = repository
        self.uow = uow
        self.agora = agora

    def execute(self, criador_id: int, nome: str, descricao: str | None,
                data_inicio: date, data_fim: date) -> Viagem:
        # criador_id vem da identidade autenticada, nunca do corpo da requisicao.
        viagem = Viagem(
            criador_id=criador_id,
            nome=nome,
            descricao=descricao,
            data_inicio=data_inicio,
            data_fim=data_fim,
            codigo_convite=gerar_codigo_convite(),
            codigo_convite_expira_em=expiracao_convite(self.agora()),
        )

        with self.uow:
            salva = self.repository.salvar(viagem)
            self.uow.commit()

        return salva
