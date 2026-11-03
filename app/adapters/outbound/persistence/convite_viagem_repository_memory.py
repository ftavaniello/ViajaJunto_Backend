from datetime import datetime, timezone

from app.domain.entities.convite_viagem import ConviteViagem
from app.domain.ports.convite_viagem_repository import ConviteViagemRepository


class ConviteViagemRepositoryMemory(ConviteViagemRepository):
    def __init__(self):
        self.convites: dict[int, ConviteViagem] = {}
        self.proximo_id = 1

    def salvar(self, convite: ConviteViagem) -> ConviteViagem:
        if convite.id is None:
            convite.id = self.proximo_id
            convite.criado_em = datetime.now(timezone.utc)
            self.proximo_id += 1
        # Copia para que alterar o objeto devolvido nao mude o "banco" sem salvar.
        self.convites[convite.id] = _copia(convite)
        return _copia(convite)

    def buscar_por_hash(self, token_hash: str) -> ConviteViagem | None:
        return next(
            (_copia(c) for c in self.convites.values() if c.token_hash == token_hash), None
        )

    def buscar(self, viagem_id: int, convite_id: int) -> ConviteViagem | None:
        convite = self.convites.get(convite_id)
        return _copia(convite) if convite and convite.viagem_id == viagem_id else None

    def listar_pendentes(self, viagem_id: int, agora: datetime) -> list[ConviteViagem]:
        return [
            _copia(c) for c in self.convites.values()
            if c.viagem_id == viagem_id and not c.aceito and not c.expirado(agora)
        ]

    def remover(self, convite_id: int) -> None:
        self.convites.pop(convite_id, None)

    def remover_pendentes(self, viagem_id: int, email: str) -> None:
        self.convites = {
            id_: c for id_, c in self.convites.items()
            if not (c.viagem_id == viagem_id and c.email == email and not c.aceito)
        }


def _copia(convite: ConviteViagem) -> ConviteViagem:
    return ConviteViagem(**vars(convite))
