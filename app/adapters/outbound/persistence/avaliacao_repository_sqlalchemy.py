from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.avaliacao_model import AvaliacaoModel
from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.domain.entities.avaliacao import Avaliacao, ReviewPublico


class SQLAlchemyAvaliacaoRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _consulta():
        return select(AvaliacaoModel, UsuarioModel.nome).outerjoin(
            UsuarioModel, AvaliacaoModel.usuario_id == UsuarioModel.id
        )

    def salvar(self, avaliacao: Avaliacao) -> ReviewPublico:
        dados = {
            campo: getattr(avaliacao, campo)
            for campo in (
                "usuario_id",
                "catalogo_atividade_id",
                "atividade_viagem_id",
                "nota",
                "comentario",
            )
        }
        comando = insert(AvaliacaoModel).values(**dados)
        comando = comando.on_conflict_do_update(
            constraint="uq_avaliacoes_usuario_atividade",
            set_={
                "nota": comando.excluded.nota,
                "comentario": comando.excluded.comentario,
                "atividade_viagem_id": comando.excluded.atividade_viagem_id,
                "atualizado_em": func.now(),
            },
        ).returning(AvaliacaoModel.id)
        review_id = self.db.scalar(comando)
        linha = self.db.execute(
            self._consulta()
            .where(AvaliacaoModel.id == review_id)
            .execution_options(populate_existing=True)
        ).one()
        return self._publico(*linha)

    def listar(self, atividade_id: int, limite: int, deslocamento: int) -> list[ReviewPublico]:
        linhas = self.db.execute(
            self._consulta()
            .where(AvaliacaoModel.catalogo_atividade_id == atividade_id)
            .order_by(AvaliacaoModel.criado_em.desc(), AvaliacaoModel.id.desc())
            .limit(limite)
            .offset(deslocamento)
            .execution_options(populate_existing=True)
        )
        return [self._publico(*linha) for linha in linhas]

    @staticmethod
    def _publico(model: AvaliacaoModel, nome: str | None) -> ReviewPublico:
        return ReviewPublico(model.id, model.nota, model.comentario, nome, model.criado_em)
