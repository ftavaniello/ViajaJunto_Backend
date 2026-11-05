from app.adapters.outbound.persistence.membro_viagem_repository_memory import (
    MembroViagemRepositoryMemory,
)
from app.domain.entities.viagem import Viagem
from app.domain.participacao_viagem import ParticipacaoViagem
from app.domain.ports.viagem_repository import ViagemRepository


class ViagemRepositoryMemory(ViagemRepository):
    def __init__(self, membros: MembroViagemRepositoryMemory | None = None):
        self.viagens: dict[int, Viagem] = {}
        self.proximo_id = 1
        # Faz o papel do JOIN/ON DELETE CASCADE com membros_viagem do banco.
        self.membros = membros or MembroViagemRepositoryMemory()

    def salvar(self, viagem: Viagem) -> Viagem:
        if viagem.id is None:
            viagem.id = self.proximo_id
            self.proximo_id += 1

        self.viagens[viagem.id] = viagem

        return viagem

    def buscar_por_id(self, viagem_id: int) -> Viagem | None:
        return self.viagens.get(viagem_id)

    def listar_por_participante(
        self, usuario_id: int, limite: int, deslocamento: int
    ) -> list[ParticipacaoViagem]:
        como_membro = self.membros.viagens_do_membro(usuario_id)
        viagens = [
            v for v in self.viagens.values()
            if v.criador_id == usuario_id or v.id in como_membro
        ]
        ordenadas = sorted(viagens, key=lambda v: (v.data_inicio, v.id))
        return [
            ParticipacaoViagem(v, self.membros.buscar_papel(v.id, usuario_id))
            for v in ordenadas[deslocamento:deslocamento + limite]
        ]

    def deletar(self, viagem_id: int) -> None:
        self.viagens.pop(viagem_id, None)
        self.membros.remover_da_viagem(viagem_id)
