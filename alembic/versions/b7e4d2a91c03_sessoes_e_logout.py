"""sessoes e logout: tokens revogados e versao de sessao do usuario

Implementa a política de docs/sessoes-e-logout.md (RF02): logout revoga o token
no servidor (`tokens_revogados`) e a troca de senha encerra todas as sessões do
usuário (`usuarios.versao_sessao`).

Revision ID: b7e4d2a91c03
Revises: a3f1c9d27b45
Create Date: 2026-10-29 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e4d2a91c03"
down_revision: Union[str, Sequence[str], None] = "a3f1c9d27b45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "usuarios",
        sa.Column("versao_sessao", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )

    op.create_table(
        "tokens_revogados",
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "revogado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index(
        op.f("ix_tokens_revogados_usuario_id"), "tokens_revogados", ["usuario_id"]
    )
    op.create_index(
        op.f("ix_tokens_revogados_expira_em"), "tokens_revogados", ["expira_em"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_tokens_revogados_expira_em"), table_name="tokens_revogados")
    op.drop_index(op.f("ix_tokens_revogados_usuario_id"), table_name="tokens_revogados")
    op.drop_table("tokens_revogados")
    op.drop_column("usuarios", "versao_sessao")
