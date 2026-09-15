"""seed usuario inicial

Revision ID: c86992485fcc
Revises: afb2f0e1885d
Create Date: 2026-09-15 18:46:11.820018

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c86992485fcc'
down_revision: Union[str, Sequence[str], None] = 'afb2f0e1885d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

usuarios = sa.table(
    "usuarios",
    sa.column("nome", sa.String),
    sa.column("email", sa.String),
    sa.column("senha_hash", sa.String),
)


def upgrade() -> None:
    """Upgrade schema."""
    # Senha ainda em texto puro: o port de hashing (passo 5 do roadmap) ainda não existe.
    op.bulk_insert(
        usuarios,
        [
            {
                "nome": "Usuario Inicial",
                "email": "usuario@viajajunto.com",
                "senha_hash": "changeme123",
            }
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        usuarios.delete().where(usuarios.c.email == "usuario@viajajunto.com")
    )
