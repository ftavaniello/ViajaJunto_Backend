from app.adapters.outbound.persistence.destino_viagem_repository_memory import (
    DestinoViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.viagem_repository_memory import ViagemRepositoryMemory
from app.domain.paises_visitados import ParadaDoParticipante
from app.domain.ports.paradas_participante_repository import ParadasParticipanteRepository


class ParadasParticipanteRepositoryMemory(ParadasParticipanteRepository):
    """Faz o papel do JOIN entre viagens, membros, paradas e catálogo do banco."""

    def __init__(self, viagens: ViagemRepositoryMemory, destinos: DestinoViagemRepositoryMemory):
        self.viagens = viagens
        self.destinos = destinos

    def listar(self, usuario_id: int) -> list[ParadaDoParticipante]:
        como_membro = self.viagens.membros.viagens_do_membro(usuario_id)
        participa = {
            v.id: v
            for v in self.viagens.viagens.values()
            if v.criador_id == usuario_id or v.id in como_membro
        }
        return [
            ParadaDoParticipante(
                viagem_id=destino.viagem_id,
                status_viagem=participa[destino.viagem_id].status,
                pais_codigo=destino.destino.pais_codigo,
                data_chegada=destino.data_chegada,
            )
            for destino in self.destinos.destinos.values()
            if destino.viagem_id in participa
        ]
