from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.outbound.persistence._constraints import check_in
from app.domain.enums import CategoriaAtividade
from app.infrastructure.database import Base


class DestinoCatalogoModel(Base):
    """Lugar reutilizável do catálogo (cidade/localidade). Não é editado por usuários."""

    __tablename__ = "destinos_catalogo"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    # ISO 3166-1 alfa-2 em maiúsculas. Base do critério de "país visitado" (D5).
    pais_codigo: Mapped[str] = mapped_column(String(2), nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    # Nome IANA (ex.: "Europe/Lisbon"), usado só para exibir horários (D6).
    fuso_horario: Mapped[str | None] = mapped_column(String(64))
    # Referência externa à foto; o sistema não armazena arquivos de imagem (D8).
    foto_url: Mapped[str | None] = mapped_column(String(500))
    google_place_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("pais_codigo = upper(pais_codigo) AND length(pais_codigo) = 2",
                        name="ck_destinos_catalogo_pais"),
        CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90",
                        name="ck_destinos_catalogo_latitude"),
        CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180",
                        name="ck_destinos_catalogo_longitude"),
        Index("ix_destinos_catalogo_pais", "pais_codigo"),
    )


class CatalogoAtividadeModel(Base):
    """Atividade reutilizável do catálogo, sempre ligada a um destino do catálogo.

    É o alvo das avaliações (RF22); a nota do destino é derivada delas (D2).
    """

    __tablename__ = "catalogo_atividades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    destino_catalogo_id: Mapped[int] = mapped_column(
        ForeignKey("destinos_catalogo.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(20), nullable=False)
    endereco: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    foto_url: Mapped[str | None] = mapped_column(String(500))
    google_place_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    fonte: Mapped[str] = mapped_column(
        String(30), nullable=False, default="manual", server_default="manual"
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        check_in("ck_catalogo_atividades_categoria", "categoria", CategoriaAtividade),
        CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90",
                        name="ck_catalogo_atividades_latitude"),
        CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180",
                        name="ck_catalogo_atividades_longitude"),
    )
