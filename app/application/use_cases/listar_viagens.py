from app.domain.entities.viagem import Viagem
from app.domain.ports.viagem_repository import ViagemRepository


class ListarViagens:
    def __init__(self, repository: ViagemRepository):
        self.repository = repository

    def execute(self, usuario_id: int) -> list[Viagem]:
        return self.repository.listar_por_participante(usuario_id)
