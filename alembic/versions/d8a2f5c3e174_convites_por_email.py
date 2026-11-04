"""convites por email (issue #16): troca o código da viagem por convites individuais

Cria `convites_viagem` (um link de uso único por email convidado, guardando só o
hash do token) e remove `viagens.codigo_convite`/`codigo_convite_expira_em`, que
permitiam a entrada de qualquer pessoa que recebesse o código.

Revision ID: d8a2f5c3e174
Revises: c6f1a4b83d02
Create Date: 2026-11-03 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "d8a2f5c3e174"
down_revision = "c6f1a4b83d02"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "convites_viagem",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("viagem_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("convidado_por_id", sa.Integer(), nullable=True),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aceito_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["viagem_id"], ["viagens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["convidado_por_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "uq_convites_viagem_pendente",
        "convites_viagem",
        ["viagem_id", "email"],
        unique=True,
        postgresql_where=sa.text("aceito_em IS NULL"),
    )

    # A UNIQUE de codigo_convite cai junto com a coluna.
    op.drop_column("viagens", "codigo_convite")
    op.drop_column("viagens", "codigo_convite_expira_em")


def downgrade():
    op.add_column("viagens", sa.Column("codigo_convite", sa.String(length=12), nullable=True))
    op.add_column(
        "viagens",
        sa.Column("codigo_convite_expira_em", sa.DateTime(timezone=True), nullable=True),
    )
    # Viagens criadas depois do upgrade não têm código; sorteia um para cada.
    op.execute(
        "UPDATE viagens SET "
        "codigo_convite = upper(substr(md5(random()::text || id::text), 1, 10)), "
        "codigo_convite_expira_em = now() + interval '7 days'"
    )
    op.alter_column("viagens", "codigo_convite", nullable=False)
    op.alter_column("viagens", "codigo_convite_expira_em", nullable=False)
    op.create_unique_constraint("viagens_codigo_convite_key", "viagens", ["codigo_convite"])

    op.drop_index("uq_convites_viagem_pendente", table_name="convites_viagem")
    op.drop_table("convites_viagem")
