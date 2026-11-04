"""identificador externo genérico no catálogo (issue #23)

Troca `google_place_id` por `fonte` + `id_externo` em destinos e atividades do
catálogo. A unicidade passa a ser por fornecedor: `UNIQUE (fonte, id_externo)`,
o que permite reimportar do Geoapify (ou de outro fornecedor) sem duplicar.
Registros existentes ficam com `fonte = 'manual'` e mantêm o valor antigo.
O downgrade preserva os registros de fornecedor como manuais, sem `id_externo`.

Revision ID: a7d3e8c25f61
Revises: e9c4b7a15d28
Create Date: 2026-11-04 20:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "a7d3e8c25f61"
down_revision = "e9c4b7a15d28"
branch_labels = None
depends_on = None

_TABELAS = ("destinos_catalogo", "catalogo_atividades")
_FONTES = "'manual', 'geoapify'"


def upgrade():
    op.add_column(
        "destinos_catalogo",
        sa.Column("fonte", sa.String(30), nullable=False, server_default="manual"),
    )
    for tabela in _TABELAS:
        op.drop_constraint(f"{tabela}_google_place_id_key", tabela, type_="unique")
        op.alter_column(tabela, "google_place_id", new_column_name="id_externo")
        op.create_unique_constraint(
            f"uq_{tabela}_fonte_id_externo", tabela, ["fonte", "id_externo"]
        )
        op.create_check_constraint(f"ck_{tabela}_fonte", tabela, f"fonte IN ({_FONTES})")


def downgrade():
    for tabela in _TABELAS:
        # O formato antigo só aceita curadoria manual com um id único global. Os
        # registros vindos de fornecedor são mantidos (avaliações e roteiros apontam
        # para eles), mas perdem a referência externa.
        op.execute(
            f"UPDATE {tabela} SET fonte = 'manual', id_externo = NULL WHERE fonte <> 'manual'"
        )
        op.drop_constraint(f"ck_{tabela}_fonte", tabela, type_="check")
        op.drop_constraint(f"uq_{tabela}_fonte_id_externo", tabela, type_="unique")
        op.alter_column(tabela, "id_externo", new_column_name="google_place_id")
        op.create_unique_constraint(f"{tabela}_google_place_id_key", tabela, ["google_place_id"])
    op.drop_column("destinos_catalogo", "fonte")
