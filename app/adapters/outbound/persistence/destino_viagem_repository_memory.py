from dataclasses import replace
from datetime import date
from typing import cast

from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.ports.destino_viagem_repository import DestinoViagemRepository


class DestinoViagemRepositoryMemory(DestinoViagemRepository):
    def __init__(self):
        self.destinos: dict[int, DestinoViagem] = {}
        self.atividades: dict[int, list[date]] = {}
        self.proximo_id = 1

    def bloquear_roteiro(self, viagem_id: int) -> None:
        # Testes do núcleo são sequenciais; o bloqueio real pertence ao PostgreSQL.
        pass

    def listar(self, viagem_id: int) -> list[DestinoViagem]:
        return sorted(
            (d for d in self.destinos.values() if d.viagem_id == viagem_id),
            key=lambda d: (d.ordem, d.id),
        )

    def buscar(self, viagem_id: int, destino_id: int) -> DestinoViagem | None:
        destino = self.destinos.get(destino_id)
        return destino if destino and destino.viagem_id == viagem_id else None

    def salvar(self, destino: DestinoViagem) -> DestinoViagem:
        if destino.id is None:
            destino = cast(DestinoViagem, replace(destino, id=self.proximo_id))
            self.proximo_id += 1
        self.destinos[destino.id] = destino
        return destino

    def deletar(self, destino: DestinoViagem) -> None:
        self.destinos.pop(destino.id, None)
        self.atividades.pop(destino.id, None)

    def datas_atividades(self, destino_id: int) -> list[date]:
        return list(self.atividades.get(destino_id, []))
