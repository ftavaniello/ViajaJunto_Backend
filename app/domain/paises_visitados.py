"""Critério de "país visitado" (RF11).

Uma parada conta como visita efetiva do usuário quando:

- o usuário participa da viagem (criador ou colaborador de qualquer papel);
- a viagem está `confirmada` ou `concluida` (viagens `planejando` são só planos);
- a data de chegada da parada já chegou (`data_chegada <= hoje`).

O país é o `pais_codigo` (ISO 3166-1 alfa-2) do destino do catálogo da parada.
Cada país aparece uma única vez, mesmo visitado em várias paradas ou viagens.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from app.domain.enums import StatusViagem

STATUS_VIAGEM_EFETIVA = frozenset({StatusViagem.CONFIRMADA, StatusViagem.CONCLUIDA})


@dataclass(frozen=True, kw_only=True)
class ParadaDoParticipante:
    """Parada de uma viagem da qual o usuário participa, com o país do destino."""

    viagem_id: int
    status_viagem: StatusViagem
    pais_codigo: str
    data_chegada: date

    def visitada(self, hoje: date) -> bool:
        return self.status_viagem in STATUS_VIAGEM_EFETIVA and self.data_chegada <= hoje


@dataclass(frozen=True, kw_only=True)
class PaisVisitado:
    pais_codigo: str
    primeira_visita: date
    ultima_visita: date
    total_viagens: int


def paises_visitados(paradas: Iterable[ParadaDoParticipante], hoje: date) -> list[PaisVisitado]:
    """Aplica o critério de visita e agrupa por país, ordenando pelo código."""
    datas: dict[str, list[date]] = {}
    viagens: dict[str, set[int]] = {}
    for parada in paradas:
        if not parada.visitada(hoje):
            continue
        datas.setdefault(parada.pais_codigo, []).append(parada.data_chegada)
        viagens.setdefault(parada.pais_codigo, set()).add(parada.viagem_id)
    return [
        PaisVisitado(
            pais_codigo=pais,
            primeira_visita=min(datas[pais]),
            ultima_visita=max(datas[pais]),
            total_viagens=len(viagens[pais]),
        )
        for pais in sorted(datas)
    ]
