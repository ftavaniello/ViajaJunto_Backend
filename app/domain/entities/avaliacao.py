from dataclasses import dataclass
from datetime import datetime

from app.domain.entities.atividade_viagem import AtividadeViagem
from app.domain.entities.catalogo import texto
from app.domain.enums import StatusAtividade
from app.domain.errors import AcessoNegado, DadosInvalidos
from app.domain.regras import NOTA_MAXIMA, NOTA_MINIMA


@dataclass(frozen=True, kw_only=True)
class Avaliacao:
    usuario_id: int
    catalogo_atividade_id: int
    atividade_viagem_id: int
    nota: int
    comentario: str | None = None

    def __post_init__(self):
        if type(self.nota) is not int or not NOTA_MINIMA <= self.nota <= NOTA_MAXIMA:
            raise DadosInvalidos("Nota deve ser um inteiro entre 1 e 5")
        object.__setattr__(self, "comentario", texto(self.comentario, "Comentário", 2000))


def exigir_realizacao(atividade: AtividadeViagem) -> None:
    # realizada_por_id identifica quem marcou a conclusão, não todos os viajantes.
    if atividade.status != StatusAtividade.CONCLUIDA or atividade.realizada_em is None:
        raise AcessoNegado("Somente atividades concluídas podem ser avaliadas")


@dataclass(frozen=True)
class ReviewPublico:
    id: int
    nota: int
    comentario: str | None
    autor_nome: str | None
    criado_em: datetime
