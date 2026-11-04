"""tipos de notificação do RF21 (issue #28): avisos de alterações no planejamento

Acrescenta `viagem_alterada`, `roteiro_alterado` e `atividade_alterada` ao CHECK de
`notificacoes.tipo`. O downgrade remove as notificações desses tipos antes de
restaurar a lista original.

Revision ID: e9c4b7a15d28
Revises: d8a2f5c3e174
Create Date: 2026-11-03 18:00:00.000000

"""

from alembic import op

revision = "e9c4b7a15d28"
down_revision = "d8a2f5c3e174"
branch_labels = None
depends_on = None

_ORIGINAIS = "'membro_entrou', 'papel_alterado', 'membro_removido', 'viagem_excluida'"
_NOVOS = "'viagem_alterada', 'roteiro_alterado', 'atividade_alterada'"


def upgrade():
    op.drop_constraint("ck_notificacoes_tipo", "notificacoes", type_="check")
    op.create_check_constraint(
        "ck_notificacoes_tipo", "notificacoes", f"tipo IN ({_ORIGINAIS}, {_NOVOS})"
    )


def downgrade():
    op.drop_constraint("ck_notificacoes_tipo", "notificacoes", type_="check")
    op.execute(f"DELETE FROM notificacoes WHERE tipo IN ({_NOVOS})")
    op.create_check_constraint("ck_notificacoes_tipo", "notificacoes", f"tipo IN ({_ORIGINAIS})")
