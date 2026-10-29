from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.regras import NOTA_MAXIMA, NOTA_MINIMA
from app.infrastructure.database import Base


class AvaliacaoModel(Base):
    """Avaliação de uma atividade do catálogo (RF22). Destino não é avaliado diretamente (D2).

    Sobrevive à exclusão da viagem e da conta de quem avaliou: `atividade_viagem_id`
    e `usuario_id` viram NULL (D10).
    """

    __tablename__ = "avaliacoes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    catalogo_atividade_id: Mapped[int] = mapped_column(
        ForeignKey("catalogo_atividades.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Comprovação (D3): a atividade da viagem marcada como realizada que habilitou a avaliação.
    atividade_viagem_id: Mapped[int | None] = mapped_column(
        ForeignKey("atividades_viagem.id", ondelete="SET NULL")
    )
    nota: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comentario: Mapped[str | None] = mapped_column(String(2000))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        # Uma avaliação por usuário e atividade do catálogo (editável, não repetível).
        UniqueConstraint(
            "usuario_id", "catalogo_atividade_id", name="uq_avaliacoes_usuario_atividade"
        ),
        CheckConstraint(
            f"nota BETWEEN {NOTA_MINIMA} AND {NOTA_MAXIMA}", name="ck_avaliacoes_nota"
        ),
    )
