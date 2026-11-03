from abc import ABC, abstractmethod

from app.domain.paises_visitados import ParadaDoParticipante


class ParadasParticipanteRepository(ABC):
    @abstractmethod
    def listar(self, usuario_id: int) -> list[ParadaDoParticipante]:
        """Paradas de todas as viagens das quais o usuário participa hoje.

        Inclui viagens criadas por ele e as compartilhadas (qualquer papel); não aplica
        o critério de visita, que fica no domínio.
        """
        pass
