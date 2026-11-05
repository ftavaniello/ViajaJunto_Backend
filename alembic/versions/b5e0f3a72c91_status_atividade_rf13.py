"""Alinha os status de atividade ao RF13 e preserva cancelamentos legados."""

import sqlalchemy as sa

from alembic import op

revision = "b5e0f3a72c91"
down_revision = ("a4d9e2f61b80", "3f1a9c2d7b40")
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_atividades_viagem_status", "atividades_viagem", type_="check")
    op.drop_constraint("ck_atividades_viagem_comprovacao", "atividades_viagem", type_="check")
    op.execute("UPDATE atividades_viagem SET status = 'pendente' WHERE status = 'planejada'")
    op.execute("UPDATE atividades_viagem SET status = 'concluida' WHERE status = 'realizada'")
    op.alter_column(
        "atividades_viagem", "status", existing_type=sa.String(20), server_default="pendente"
    )
    op.create_check_constraint(
        "ck_atividades_viagem_status",
        "atividades_viagem",
        "status IN ('pendente', 'confirmada', 'concluida', 'cancelada')",
    )
    op.create_check_constraint(
        "ck_atividades_viagem_comprovacao",
        "atividades_viagem",
        "status <> 'concluida' OR realizada_em IS NOT NULL",
    )


def downgrade():
    op.drop_constraint("ck_atividades_viagem_status", "atividades_viagem", type_="check")
    op.drop_constraint("ck_atividades_viagem_comprovacao", "atividades_viagem", type_="check")
    op.execute(
        "UPDATE atividades_viagem SET status = 'planejada' "
        "WHERE status IN ('pendente', 'confirmada')"
    )
    op.execute("UPDATE atividades_viagem SET status = 'realizada' WHERE status = 'concluida'")
    op.alter_column(
        "atividades_viagem", "status", existing_type=sa.String(20), server_default="planejada"
    )
    op.create_check_constraint(
        "ck_atividades_viagem_status",
        "atividades_viagem",
        "status IN ('planejada', 'realizada', 'cancelada')",
    )
    op.create_check_constraint(
        "ck_atividades_viagem_comprovacao",
        "atividades_viagem",
        "status <> 'realizada' OR realizada_em IS NOT NULL",
    )
