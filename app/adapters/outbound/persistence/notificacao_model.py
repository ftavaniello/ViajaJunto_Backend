from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.outbound.persistence._constraints import check_in
from app.domain.enums import TipoNotificacao
from app.infrastructure.database import Base


class NotificacaoModel(Base):
    """Notificação in-app (RF21), uma linha por destinatário."""

    __tablename__ = "notificacoes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    # SET NULL: a notificação "viagem excluída" precisa sobreviver à viagem (D10).
    viagem_id: Mapped[int | None] = mapped_column(ForeignKey("viagens.id", ondelete="SET NULL"))
    # Quem causou o evento (ex.: quem entrou na viagem); nulo se a conta foi excluída.
    ator_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    # Texto final já montado, para não depender de dados que podem ter sido excluídos.
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    lida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        check_in("ck_notificacoes_tipo", "tipo", TipoNotificacao),
        # Listagem do usuário (não lidas primeiro, mais recentes antes) e contador de não lidas.
        Index("ix_notificacoes_usuario_lida_criado", "usuario_id", "lida_em", "criado_em"),
    )
