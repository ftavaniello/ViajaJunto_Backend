from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base

# Nome gerado pelo PostgreSQL para a constraint criada na migracao inicial.
USUARIOS_EMAIL_UNIQUE = "usuarios_email_key"


class UsuarioModel(Base):
    __tablename__ = "usuarios"
    __table_args__ = (UniqueConstraint("email", name=USUARIOS_EMAIL_UNIQUE),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    versao_sessao: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
