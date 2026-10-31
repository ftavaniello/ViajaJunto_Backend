from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class TokenRevogadoModel(Base):
    """Token de acesso encerrado por logout (RF02).

    Guarda só o `jti` do JWT, nunca o token. A linha só importa até `expira_em`:
    depois disso o próprio JWT já é recusado, e ela pode ser apagada.
    """

    __tablename__ = "tokens_revogados"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expira_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revogado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
