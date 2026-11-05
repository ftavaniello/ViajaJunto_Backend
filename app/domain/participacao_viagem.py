from dataclasses import dataclass

from app.domain.entities.viagem import Viagem
from app.domain.enums import PapelMembro


@dataclass(frozen=True)
class ParticipacaoViagem:
    viagem: Viagem
    papel_membro: PapelMembro | None
