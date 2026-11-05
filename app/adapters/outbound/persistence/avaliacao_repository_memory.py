from datetime import datetime, timezone
from decimal import Decimal

from app.domain.entities.avaliacao import Avaliacao, ReviewPublico
from app.domain.ports.usuario_repository import UsuarioRepository


class AvaliacaoRepositoryMemory:
    def __init__(self, usuarios: UsuarioRepository):
        self.usuarios = usuarios
        self.avaliacoes: dict[tuple[int, int], Avaliacao] = {}
        self.reviews: dict[tuple[int, int], ReviewPublico] = {}

    def salvar(self, avaliacao: Avaliacao) -> ReviewPublico:
        chave = (avaliacao.usuario_id, avaliacao.catalogo_atividade_id)
        anterior = self.reviews.get(chave)
        self.avaliacoes[chave] = avaliacao
        usuario = self.usuarios.buscar_por_id(avaliacao.usuario_id)
        review = ReviewPublico(
            anterior.id if anterior else len(self.reviews) + 1,
            avaliacao.nota,
            avaliacao.comentario,
            usuario.nome if usuario else None,
            anterior.criado_em if anterior else datetime.now(timezone.utc),
        )
        self.reviews[chave] = review
        return review

    def listar(self, atividade_id: int, limite: int, deslocamento: int) -> list[ReviewPublico]:
        reviews = []
        for (usuario_id, catalogo_id), review in self.reviews.items():
            if catalogo_id == atividade_id:
                usuario = self.usuarios.buscar_por_id(usuario_id)
                reviews.append(
                    ReviewPublico(
                        review.id,
                        review.nota,
                        review.comentario,
                        usuario.nome if usuario else None,
                        review.criado_em,
                    )
                )
        reviews.sort(key=lambda r: (r.criado_em, r.id), reverse=True)
        return reviews[deslocamento : deslocamento + limite]

    def resumo(self, atividade_id: int) -> tuple[Decimal | None, int]:
        notas = [
            a.nota for a in self.avaliacoes.values() if a.catalogo_atividade_id == atividade_id
        ]
        return (Decimal(sum(notas)) / len(notas), len(notas)) if notas else (None, 0)
