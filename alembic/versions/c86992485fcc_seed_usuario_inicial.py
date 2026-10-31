"""seed usuario inicial

Revision ID: c86992485fcc
Revises: afb2f0e1885d
Create Date: 2026-09-15 18:46:11.820018

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "c86992485fcc"
down_revision: Union[str, Sequence[str], None] = "afb2f0e1885d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Esta revisao inseria uma conta de demonstracao com senha conhecida em todo
    # banco migrado, inclusive producao. O seed agora e opcional e separado do
    # provisionamento: `python -m app.adapters.inbound.cli.seed_demo` (so em
    # desenvolvimento). A revisao continua na cadeia para nao quebrar bancos que
    # ja a aplicaram; nesses, a conta existente e preservada como esta.


def downgrade() -> None:
    """Downgrade schema."""
    # Nada a desfazer: a revisao nao altera mais dados. Contas existentes,
    # inclusive a de demonstracao, nao sao apagadas por downgrade.
