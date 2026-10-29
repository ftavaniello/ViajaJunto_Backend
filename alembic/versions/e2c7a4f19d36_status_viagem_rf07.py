"""status da viagem conforme RF07: planejando, confirmada e concluida

O modelo v1 previa `em_andamento` e `cancelada`; RF07 define "Em planejamento",
"Confirmada" e "Concluída". Linhas existentes são convertidas antes de trocar o
CHECK: `em_andamento` vira `confirmada` e `cancelada` vira `concluida` (viagem
encerrada). Até esta revisão nenhuma rota gravava viagens.

Revision ID: e2c7a4f19d36
Revises: a3f1c9d27b45
Create Date: 2026-10-29 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2c7a4f19d36"
down_revision: Union[str, Sequence[str], None] = "a3f1c9d27b45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("ck_viagens_status", "viagens", type_="check")
    op.execute("UPDATE viagens SET status = 'confirmada' WHERE status = 'em_andamento'")
    op.execute("UPDATE viagens SET status = 'concluida' WHERE status = 'cancelada'")
    op.create_check_constraint(
        "ck_viagens_status", "viagens", "status IN ('planejando', 'confirmada', 'concluida')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_viagens_status", "viagens", type_="check")
    op.execute("UPDATE viagens SET status = 'em_andamento' WHERE status = 'confirmada'")
    op.create_check_constraint(
        "ck_viagens_status",
        "viagens",
        "status IN ('planejando', 'em_andamento', 'concluida', 'cancelada')",
    )
