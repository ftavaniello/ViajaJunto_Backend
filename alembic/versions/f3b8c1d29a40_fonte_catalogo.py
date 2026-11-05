"""Registra a origem dos dados do catálogo interno."""

import sqlalchemy as sa

from alembic import op

revision = "f3b8c1d29a40"
down_revision = "e2c7a4f19d36"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "catalogo_atividades",
        sa.Column(
            "fonte",
            sa.String(30),
            nullable=False,
            server_default="manual",
        ),
    )


def downgrade():
    op.drop_column("catalogo_atividades", "fonte")
