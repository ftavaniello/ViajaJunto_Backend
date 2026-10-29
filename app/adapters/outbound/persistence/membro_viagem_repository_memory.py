from app.domain.enums import PapelMembro
from app.domain.ports.membro_viagem_repository import MembroViagemRepository


class MembroViagemRepositoryMemory(MembroViagemRepository):
    def __init__(self):
        self.papeis: dict[tuple[int, int], PapelMembro] = {}

    def adicionar(self, viagem_id: int, usuario_id: int, papel: PapelMembro) -> None:
        # Ainda nao faz parte da porta: a entrada de membros chega com os convites.
        self.papeis[(viagem_id, usuario_id)] = papel

    def buscar_papel(self, viagem_id: int, usuario_id: int) -> PapelMembro | None:
        return self.papeis.get((viagem_id, usuario_id))

    def viagens_do_membro(self, usuario_id: int) -> set[int]:
        return {viagem_id for viagem_id, membro_id in self.papeis if membro_id == usuario_id}

    def remover_da_viagem(self, viagem_id: int) -> None:
        self.papeis = {chave: p for chave, p in self.papeis.items() if chave[0] != viagem_id}
