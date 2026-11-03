from datetime import datetime, timezone

from app.domain.enums import PapelMembro
from app.domain.errors import MembroJaParticipa
from app.domain.membro_viagem import MembroViagem
from app.domain.ports.membro_viagem_repository import MembroViagemRepository


class MembroViagemRepositoryMemory(MembroViagemRepository):
    def __init__(self):
        # dict preserva a ordem de insercao, que faz o papel de `entrou_em`.
        self.papeis: dict[tuple[int, int], PapelMembro] = {}
        self.entradas: dict[tuple[int, int], datetime] = {}

    def adicionar(self, viagem_id: int, usuario_id: int, papel: PapelMembro) -> None:
        # Mesmo efeito da constraint uq_membros_viagem_viagem_usuario do banco.
        if (viagem_id, usuario_id) in self.papeis:
            raise MembroJaParticipa("Você já participa desta viagem")
        self.papeis[(viagem_id, usuario_id)] = papel
        self.entradas[(viagem_id, usuario_id)] = datetime.now(timezone.utc)

    def alterar_papel(self, viagem_id: int, usuario_id: int, papel: PapelMembro) -> None:
        if (viagem_id, usuario_id) in self.papeis:
            self.papeis[(viagem_id, usuario_id)] = papel

    def remover(self, viagem_id: int, usuario_id: int) -> None:
        self.papeis.pop((viagem_id, usuario_id), None)
        self.entradas.pop((viagem_id, usuario_id), None)

    def listar(self, viagem_id: int) -> list[MembroViagem]:
        return [
            MembroViagem(usuario_id, papel, self.entradas.get((v_id, usuario_id)))
            for (v_id, usuario_id), papel in self.papeis.items()
            if v_id == viagem_id
        ]

    def buscar_papel(self, viagem_id: int, usuario_id: int) -> PapelMembro | None:
        return self.papeis.get((viagem_id, usuario_id))

    def viagens_do_membro(self, usuario_id: int) -> set[int]:
        return {viagem_id for viagem_id, membro_id in self.papeis if membro_id == usuario_id}

    def remover_da_viagem(self, viagem_id: int) -> None:
        self.papeis = {chave: p for chave, p in self.papeis.items() if chave[0] != viagem_id}
        self.entradas = {
            chave: e for chave, e in self.entradas.items() if chave[0] != viagem_id
        }
