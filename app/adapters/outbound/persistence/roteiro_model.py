from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.outbound.persistence._constraints import check_in
from app.domain.enums import StatusAtividade
from app.infrastructure.database import Base


class DestinoViagemModel(Base):
    """Parada da viagem: um destino do catálogo em uma posição da ordem de visita."""

    __tablename__ = "destinos_viagem"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    viagem_id: Mapped[int] = mapped_column(
        ForeignKey("viagens.id", ondelete="CASCADE"), nullable=False
    )
    destino_catalogo_id: Mapped[int] = mapped_column(
        ForeignKey("destinos_catalogo.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    # Datas de calendário no local do destino, sem fuso (D6).
    data_chegada: Mapped[date] = mapped_column(Date, nullable=False)
    data_saida: Mapped[date] = mapped_column(Date, nullable=False)
    hospedagem: Mapped[str | None] = mapped_column(String(255))
    observacoes: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # Adiado até o fim da transação para permitir reordenar paradas (trocar posições).
        UniqueConstraint(
            "viagem_id", "ordem", name="uq_destinos_viagem_ordem",
            deferrable=True, initially="DEFERRED",
        ),
        CheckConstraint("ordem >= 1", name="ck_destinos_viagem_ordem"),
        CheckConstraint("data_saida >= data_chegada", name="ck_destinos_viagem_periodo"),
    )


class AtividadeViagemModel(Base):
    """Atividade de um destino da viagem: horário, duração, custo previsto e status."""

    __tablename__ = "atividades_viagem"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    destino_viagem_id: Mapped[int] = mapped_column(
        ForeignKey("destinos_viagem.id", ondelete="CASCADE"), nullable=False, index=True
    )
    catalogo_atividade_id: Mapped[int] = mapped_column(
        ForeignKey("catalogo_atividades.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    data: Mapped[date] = mapped_column(Date, nullable=False)
    # Horário de relógio no local do destino, sem fuso (D6).
    hora_inicio: Mapped[time | None] = mapped_column(Time)
    duracao_minutos: Mapped[int | None] = mapped_column(Integer)
    # Na moeda da viagem (D7).
    custo_previsto: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=StatusAtividade.PENDENTE.value,
        server_default=StatusAtividade.PENDENTE.value,
    )
    # Comprovação da conclusão: nomes físicos mantidos por compatibilidade.
    realizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    realizada_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )

    __table_args__ = (
        check_in("ck_atividades_viagem_status", "status", StatusAtividade),
        CheckConstraint("custo_previsto >= 0", name="ck_atividades_viagem_custo"),
        CheckConstraint(
            "duracao_minutos IS NULL OR duracao_minutos > 0", name="ck_atividades_viagem_duracao"
        ),
        CheckConstraint(
            "status <> 'concluida' OR realizada_em IS NOT NULL",
            name="ck_atividades_viagem_comprovacao",
        ),
    )
