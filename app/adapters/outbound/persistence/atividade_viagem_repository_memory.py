from dataclasses import replace
from datetime import time
from typing import cast

from app.domain.entities.atividade_viagem import AtividadeViagem
from app.domain.ports.atividade_viagem_repository import AtividadeViagemRepository


class AtividadeViagemRepositoryMemory(AtividadeViagemRepository):
    def __init__(self):
        self.atividades: dict[int, AtividadeViagem] = {}
        self.proximo_id = 1

    def listar(self, viagem_id: int, destino_id: int) -> list[AtividadeViagem]:
        return sorted(
            (
                a
                for a in self.atividades.values()
                if a.viagem_id == viagem_id and a.destino_viagem_id == destino_id
            ),
            key=lambda a: (a.data, a.hora_inicio is None, a.hora_inicio or time.min, a.id),
        )

    def buscar(self, viagem_id: int, destino_id: int, atividade_id: int) -> AtividadeViagem | None:
        atividade = self.atividades.get(atividade_id)
        if atividade and (atividade.viagem_id, atividade.destino_viagem_id) == (
            viagem_id,
            destino_id,
        ):
            return atividade
        return None

    def salvar(self, atividade: AtividadeViagem) -> AtividadeViagem:
        if atividade.id is None:
            atividade = cast(AtividadeViagem, replace(atividade, id=self.proximo_id))
            self.proximo_id += 1
        self.atividades[atividade.id] = atividade
        return atividade

    def deletar(self, atividade: AtividadeViagem) -> None:
        self.atividades.pop(atividade.id, None)
