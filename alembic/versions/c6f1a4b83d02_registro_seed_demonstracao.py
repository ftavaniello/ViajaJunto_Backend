"""Registra cargas sem inserir dados de exemplo na migração."""

import sqlalchemy as sa

from alembic import op

revision = "c6f1a4b83d02"
down_revision = "b5e0f3a72c91"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "seeds_demonstracao",
        sa.Column("chave", sa.String(80), primary_key=True),
        sa.Column("manifesto", sa.JSON(), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade():
    op.drop_table("seeds_demonstracao")
