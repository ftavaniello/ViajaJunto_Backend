"""Completa dados descritivos do catálogo de destinos, preservando os registros."""

import sqlalchemy as sa

from alembic import op

revision = "a4d9e2f61b80"
down_revision = "f3b8c1d29a40"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "destinos_catalogo",
        sa.Column(
            "categoria",
            sa.String(20),
            nullable=False,
            server_default="cidade",
        ),
    )
    op.add_column("destinos_catalogo", sa.Column("descricao", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_destinos_catalogo_categoria",
        "destinos_catalogo",
        "categoria IN ('cidade', 'praia', 'natureza', 'cultural')",
    )


def downgrade():
    op.drop_constraint("ck_destinos_catalogo_categoria", "destinos_catalogo", type_="check")
    op.drop_column("destinos_catalogo", "descricao")
    op.drop_column("destinos_catalogo", "categoria")
