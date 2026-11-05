from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base

CONVITES_VIAGEM_PENDENTE_UNIQUE = "uq_convites_viagem_pendente"


class ConviteViagemModel(Base):
    """Convite por email para uma viagem (RF18).

    Guarda só o hash SHA-256 (hex) do token; o valor original existe apenas no
    link enviado por email. Uso único: `aceito_em` preenchido encerra o convite.
    """

    __tablename__ = "convites_viagem"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    viagem_id: Mapped[int] = mapped_column(
        ForeignKey("viagens.id", ondelete="CASCADE"), nullable=False
    )
    # Sempre em minúsculas; o convidado pode ainda não ter conta.
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # SET NULL: o histórico do aceite sobrevive à exclusão da conta de quem convidou.
    convidado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aceito_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # No máximo um convite pendente por email em cada viagem; reenviar troca o link.
        Index(
            CONVITES_VIAGEM_PENDENTE_UNIQUE,
            "viagem_id",
            "email",
            unique=True,
            postgresql_where=text("aceito_em IS NULL"),
        ),
    )
