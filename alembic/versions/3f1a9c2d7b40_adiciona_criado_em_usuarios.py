"""adiciona criado_em em usuarios

Revision ID: 3f1a9c2d7b40
Revises: 7059dc664d50
Create Date: 2026-10-29 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f1a9c2d7b40"
down_revision: Union[str, Sequence[str], None] = "7059dc664d50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Contas ja existentes recebem o horario desta migracao, pois a data real
    # de cadastro nao foi registrada antes.
    op.add_column(
        "usuarios",
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("usuarios", "criado_em")
