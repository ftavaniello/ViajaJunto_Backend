"""modelo de dados v1: viagens, catalogo, avaliacoes, notificacoes e recuperacao de senha

Implementa as decisões de docs/decisoes-de-produto.md (issue de definição do
produto e do modelo de dados). Os valores de CHECK são copiados de propósito
(não importados do domínio): uma migração precisa continuar reproduzível mesmo
que os enums mudem depois.

Revision ID: a3f1c9d27b45
Revises: 7059dc664d50
Create Date: 2026-10-27 18:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f1c9d27b45"
down_revision: Union[str, Sequence[str], None] = "7059dc664d50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamptz(nome: str, **kw) -> sa.Column:
    return sa.Column(nome, sa.DateTime(timezone=True), **kw)


def upgrade() -> None:
    """Upgrade schema."""
    # --- usuarios: criado_em (linhas existentes recebem o horário da migração) ---
    op.add_column(
        "usuarios",
        _timestamptz("criado_em", nullable=False, server_default=sa.func.now()),
        if_not_exists=True,  # Compatibilidade com a revisão paralela 3f1a9c2d7b40.
    )

    # --- viagens ---
    op.create_table(
        "viagens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("criador_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="planejando", nullable=False),
        sa.Column("moeda", sa.String(length=3), server_default="BRL", nullable=False),
        sa.Column("codigo_convite", sa.String(length=12), nullable=False),
        _timestamptz("codigo_convite_expira_em", nullable=False),
        _timestamptz("criado_em", nullable=False, server_default=sa.func.now()),
        _timestamptz("atualizado_em", nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["criador_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo_convite"),
        sa.CheckConstraint("data_fim >= data_inicio", name="ck_viagens_periodo"),
        sa.CheckConstraint("length(moeda) = 3", name="ck_viagens_moeda"),
        sa.CheckConstraint(
            "status IN ('planejando', 'em_andamento', 'concluida', 'cancelada')",
            name="ck_viagens_status",
        ),
    )
    op.create_index("ix_viagens_criador_status", "viagens", ["criador_id", "status"])

    # --- membros_viagem (o criador NÃO entra aqui; ver viagens.criador_id) ---
    op.create_table(
        "membros_viagem",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("viagem_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("papel", sa.String(length=20), nullable=False),
        _timestamptz("entrou_em", nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["viagem_id"], ["viagens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("viagem_id", "usuario_id", name="uq_membros_viagem_viagem_usuario"),
        sa.CheckConstraint(
            "papel IN ('editor', 'visualizador')", name="ck_membros_viagem_papel"
        ),
    )
    op.create_index("ix_membros_viagem_usuario_id", "membros_viagem", ["usuario_id"])

    # --- orcamentos (1:1 com viagem) ---
    op.create_table(
        "orcamentos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("viagem_id", sa.Integer(), nullable=False),
        sa.Column("limite_total", sa.Numeric(precision=12, scale=2), nullable=True),
        _timestamptz("atualizado_em", nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["viagem_id"], ["viagens.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("viagem_id"),
        sa.CheckConstraint(
            "limite_total IS NULL OR limite_total >= 0", name="ck_orcamentos_limite"
        ),
    )

    # --- catálogo ---
    op.create_table(
        "destinos_catalogo",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("pais_codigo", sa.String(length=2), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("fuso_horario", sa.String(length=64), nullable=True),
        sa.Column("foto_url", sa.String(length=500), nullable=True),
        sa.Column("google_place_id", sa.String(length=255), nullable=True),
        _timestamptz("criado_em", nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_place_id"),
        sa.CheckConstraint(
            "pais_codigo = upper(pais_codigo) AND length(pais_codigo) = 2",
            name="ck_destinos_catalogo_pais",
        ),
        sa.CheckConstraint(
            "latitude IS NULL OR latitude BETWEEN -90 AND 90",
            name="ck_destinos_catalogo_latitude",
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180",
            name="ck_destinos_catalogo_longitude",
        ),
    )
    op.create_index("ix_destinos_catalogo_pais", "destinos_catalogo", ["pais_codigo"])

    op.create_table(
        "catalogo_atividades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("destino_catalogo_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("categoria", sa.String(length=20), nullable=False),
        sa.Column("endereco", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("foto_url", sa.String(length=500), nullable=True),
        sa.Column("google_place_id", sa.String(length=255), nullable=True),
        _timestamptz("criado_em", nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["destino_catalogo_id"], ["destinos_catalogo.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_place_id"),
        sa.CheckConstraint(
            "categoria IN ('alimentacao', 'transporte', 'cultura', 'lazer', 'compras', 'outros')",
            name="ck_catalogo_atividades_categoria",
        ),
        sa.CheckConstraint(
            "latitude IS NULL OR latitude BETWEEN -90 AND 90",
            name="ck_catalogo_atividades_latitude",
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180",
            name="ck_catalogo_atividades_longitude",
        ),
    )
    op.create_index(
        "ix_catalogo_atividades_destino_catalogo_id", "catalogo_atividades", ["destino_catalogo_id"]
    )

    # --- roteiro da viagem ---
    op.create_table(
        "destinos_viagem",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("viagem_id", sa.Integer(), nullable=False),
        sa.Column("destino_catalogo_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("data_chegada", sa.Date(), nullable=False),
        sa.Column("data_saida", sa.Date(), nullable=False),
        sa.Column("hospedagem", sa.String(length=255), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        _timestamptz("criado_em", nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["viagem_id"], ["viagens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["destino_catalogo_id"], ["destinos_catalogo.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "viagem_id",
            "ordem",
            name="uq_destinos_viagem_ordem",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.CheckConstraint("ordem >= 1", name="ck_destinos_viagem_ordem"),
        sa.CheckConstraint("data_saida >= data_chegada", name="ck_destinos_viagem_periodo"),
    )
    op.create_index(
        "ix_destinos_viagem_destino_catalogo_id", "destinos_viagem", ["destino_catalogo_id"]
    )

    op.create_table(
        "atividades_viagem",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("destino_viagem_id", sa.Integer(), nullable=False),
        sa.Column("catalogo_atividade_id", sa.Integer(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("hora_inicio", sa.Time(), nullable=True),
        sa.Column("duracao_minutos", sa.Integer(), nullable=True),
        sa.Column(
            "custo_previsto", sa.Numeric(precision=12, scale=2), server_default="0", nullable=False
        ),
        sa.Column("status", sa.String(length=20), server_default="planejada", nullable=False),
        _timestamptz("realizada_em", nullable=True),
        sa.Column("realizada_por_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["destino_viagem_id"], ["destinos_viagem.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["catalogo_atividade_id"], ["catalogo_atividades.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["realizada_por_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('planejada', 'realizada', 'cancelada')",
            name="ck_atividades_viagem_status",
        ),
        sa.CheckConstraint("custo_previsto >= 0", name="ck_atividades_viagem_custo"),
        sa.CheckConstraint(
            "duracao_minutos IS NULL OR duracao_minutos > 0", name="ck_atividades_viagem_duracao"
        ),
        sa.CheckConstraint(
            "status <> 'realizada' OR realizada_em IS NOT NULL",
            name="ck_atividades_viagem_comprovacao",
        ),
    )
    op.create_index(
        "ix_atividades_viagem_destino_viagem_id", "atividades_viagem", ["destino_viagem_id"]
    )
    op.create_index(
        "ix_atividades_viagem_catalogo_atividade_id", "atividades_viagem", ["catalogo_atividade_id"]
    )

    # --- avaliações (de atividades do catálogo) ---
    op.create_table(
        "avaliacoes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("catalogo_atividade_id", sa.Integer(), nullable=False),
        sa.Column("atividade_viagem_id", sa.Integer(), nullable=True),
        sa.Column("nota", sa.SmallInteger(), nullable=False),
        sa.Column("comentario", sa.String(length=2000), nullable=True),
        _timestamptz("criado_em", nullable=False, server_default=sa.func.now()),
        _timestamptz("atualizado_em", nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["catalogo_atividade_id"], ["catalogo_atividades.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["atividade_viagem_id"], ["atividades_viagem.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "usuario_id", "catalogo_atividade_id", name="uq_avaliacoes_usuario_atividade"
        ),
        sa.CheckConstraint("nota BETWEEN 1 AND 5", name="ck_avaliacoes_nota"),
    )
    op.create_index("ix_avaliacoes_catalogo_atividade_id", "avaliacoes", ["catalogo_atividade_id"])

    # --- notificações in-app ---
    op.create_table(
        "notificacoes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("viagem_id", sa.Integer(), nullable=True),
        sa.Column("ator_id", sa.Integer(), nullable=True),
        sa.Column("mensagem", sa.Text(), nullable=False),
        _timestamptz("lida_em", nullable=True),
        _timestamptz("criado_em", nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["viagem_id"], ["viagens.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ator_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "tipo IN ('membro_entrou', 'papel_alterado', 'membro_removido', 'viagem_excluida')",
            name="ck_notificacoes_tipo",
        ),
    )
    op.create_index(
        "ix_notificacoes_usuario_lida_criado",
        "notificacoes",
        ["usuario_id", "lida_em", "criado_em"],
    )

    # --- recuperação de senha ---
    op.create_table(
        "tokens_recuperacao_senha",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        _timestamptz("expira_em", nullable=False),
        _timestamptz("usado_em", nullable=True),
        _timestamptz("criado_em", nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_tokens_recuperacao_senha_usuario_id", "tokens_recuperacao_senha", ["usuario_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("tokens_recuperacao_senha")
    op.drop_table("notificacoes")
    op.drop_table("avaliacoes")
    op.drop_table("atividades_viagem")
    op.drop_table("destinos_viagem")
    op.drop_table("catalogo_atividades")
    op.drop_table("destinos_catalogo")
    op.drop_table("orcamentos")
    op.drop_table("membros_viagem")
    op.drop_table("viagens")
    op.drop_column("usuarios", "criado_em")
