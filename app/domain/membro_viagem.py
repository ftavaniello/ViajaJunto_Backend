from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import PapelMembro
from app.domain.permissoes import PerfilViagem


@dataclass(frozen=True)
class MembroViagem:
    """Vínculo de um colaborador com a viagem (o criador não é membro)."""

    usuario_id: int
    papel: PapelMembro
    entrou_em: datetime | None = None


@dataclass(frozen=True)
class ParticipanteViagem:
    """Quem participa da viagem, inclusive o criador, para exibição."""

    usuario_id: int
    nome: str
    email: str
    perfil: PerfilViagem
    entrou_em: datetime | None
