from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.outbound.persistence._constraints import check_in
from app.domain.enums import PapelMembro, StatusViagem
from app.domain.regras import MOEDA_PADRAO
from app.infrastructure.database import Base


class ViagemModel(Base):
    """Viagem.

    `id` é a chave técnica (inteiro, como `usuarios.id`) e é a única usada em
    chaves estrangeiras. `codigo_convite` é um segredo de compartilhamento,
    separado do id e regenerável (D1 e D4 em docs/decisoes-de-produto.md).
    """

    __tablename__ = "viagens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    criador_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    # Datas de calendário, sem fuso (D6).
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=StatusViagem.PLANEJANDO.value,
        server_default=StatusViagem.PLANEJANDO.value,
    )
    # Uma moeda por viagem, ISO 4217 (D7).
    moeda: Mapped[str] = mapped_column(
        String(3), nullable=False, default=MOEDA_PADRAO, server_default=MOEDA_PADRAO
    )
    codigo_convite: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)
    codigo_convite_expira_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("data_fim >= data_inicio", name="ck_viagens_periodo"),
        CheckConstraint("length(moeda) = 3", name="ck_viagens_moeda"),
        check_in("ck_viagens_status", "status", StatusViagem),
    )


class MembroViagemModel(Base):
    """Colaborador (editor ou visualizador). O criador fica em `viagens.criador_id`."""

    __tablename__ = "membros_viagem"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    viagem_id: Mapped[int] = mapped_column(
        ForeignKey("viagens.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    papel: Mapped[str] = mapped_column(String(20), nullable=False)
    entrou_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("viagem_id", "usuario_id", name="uq_membros_viagem_viagem_usuario"),
        check_in("ck_membros_viagem_papel", "papel", PapelMembro),
    )


class OrcamentoModel(Base):
    """Orçamento da viagem (1:1). `limite_total` nulo = limite ainda não definido."""

    __tablename__ = "orcamentos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    viagem_id: Mapped[int] = mapped_column(
        ForeignKey("viagens.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    limite_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("limite_total IS NULL OR limite_total >= 0", name="ck_orcamentos_limite"),
    )


# Índice usado pelo painel "minhas viagens" (RF06).
Index("ix_viagens_criador_status", ViagemModel.criador_id, ViagemModel.status)
