from typing import Protocol

from app.domain.entities.avaliacao import Avaliacao, ReviewPublico


class AvaliacaoRepository(Protocol):
    def salvar(self, avaliacao: Avaliacao) -> ReviewPublico:
        """Insere ou atualiza atomicamente por usuário e atividade do catálogo."""
        ...

    def listar(self, atividade_id: int, limite: int, deslocamento: int) -> list[ReviewPublico]:
        """Mais recentes primeiro, por criado_em e id; somente dados públicos."""
        ...
