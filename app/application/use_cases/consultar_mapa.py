from collections.abc import Callable
from datetime import date, datetime, timezone

from app.application.acesso_viagem import PoliticaAcessoViagem
from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.paises_visitados import PaisVisitado, paises_visitados
from app.domain.permissoes import AcaoViagem
from app.domain.ports.destino_viagem_repository import DestinoViagemRepository
from app.domain.ports.paradas_participante_repository import ParadasParticipanteRepository


def _hoje_utc() -> date:
    return datetime.now(timezone.utc).date()


class ConsultarPaisesVisitados:
    """Países visitados pelo próprio usuário autenticado (RF11)."""

    def __init__(
        self, paradas: ParadasParticipanteRepository, hoje: Callable[[], date] = _hoje_utc
    ):
        self.paradas = paradas
        self.hoje = hoje

    def execute(self, usuario_id: int) -> list[PaisVisitado]:
        return paises_visitados(self.paradas.listar(usuario_id), self.hoje())


class ConsultarMapaViagem:
    """Paradas da viagem, na ordem de visita, com coordenadas para desenhar o roteiro."""

    def __init__(self, destinos: DestinoViagemRepository, acesso: PoliticaAcessoViagem):
        self.destinos = destinos
        self.acesso = acesso

    def execute(self, viagem_id: int, usuario_id: int) -> list[DestinoViagem]:
        self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.CONSULTAR)
        return self.destinos.listar(viagem_id)
