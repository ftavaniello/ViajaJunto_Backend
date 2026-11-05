"""hash senha seed usuario

Revision ID: 7059dc664d50
Revises: c86992485fcc
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

import bcrypt
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7059dc664d50"
down_revision: Union[str, Sequence[str], None] = "c86992485fcc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

usuarios = sa.table(
    "usuarios",
    sa.column("email", sa.String),
    sa.column("senha_hash", sa.String),
)

EMAIL_SEED = "usuario@viajajunto.com"
SENHA_SEED = "changeme123"


def upgrade() -> None:
    """Upgrade schema."""
    # O seed antigo gravou a senha em texto puro. So converte para bcrypt se o
    # registro ainda tiver exatamente esse valor: uma conta com o mesmo email
    # cuja senha ja e um hash (trocada ou cadastrada pela API) nao e tocada.
    senha_hash = bcrypt.hashpw(SENHA_SEED.encode(), bcrypt.gensalt()).decode()

    op.execute(
        usuarios.update()
        .where(usuarios.c.email == EMAIL_SEED, usuarios.c.senha_hash == SENHA_SEED)
        .values(senha_hash=senha_hash)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Nao volta a gravar senha em texto puro: o hash continua valido para login.
