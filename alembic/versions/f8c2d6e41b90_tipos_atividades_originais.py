"""Alinha os tipos de atividades ao documento original, preservando os vínculos.

Revision ID: f8c2d6e41b90
Revises: a7d3e8c25f61

A conversão é muitos-para-um. O downgrade usa categorias antigas canônicas:
passeio -> cultura, hospedagem/outro -> outros. Não recupera distinções antigas
entre cultura/lazer e compras/outros. Não remove registros ou altera seus IDs.
"""

from alembic import op

revision = "f8c2d6e41b90"
down_revision = "a7d3e8c25f61"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_catalogo_atividades_categoria", "catalogo_atividades", type_="check")
    op.execute("""
        UPDATE catalogo_atividades SET categoria = CASE categoria
            WHEN 'alimentacao' THEN 'refeicao'
            WHEN 'cultura' THEN 'passeio'
            WHEN 'lazer' THEN 'passeio'
            WHEN 'compras' THEN 'outro'
            WHEN 'outros' THEN 'outro'
            ELSE categoria END
    """)
    op.create_check_constraint(
        "ck_catalogo_atividades_categoria",
        "catalogo_atividades",
        "categoria IN ('passeio','refeicao','hospedagem','transporte','outro')",
    )


def downgrade():
    op.drop_constraint("ck_catalogo_atividades_categoria", "catalogo_atividades", type_="check")
    op.execute("""
        UPDATE catalogo_atividades SET categoria = CASE categoria
            WHEN 'refeicao' THEN 'alimentacao'
            WHEN 'passeio' THEN 'cultura'
            WHEN 'hospedagem' THEN 'outros'
            WHEN 'outro' THEN 'outros'
            ELSE categoria END
    """)
    op.create_check_constraint(
        "ck_catalogo_atividades_categoria",
        "catalogo_atividades",
        "categoria IN ('alimentacao','transporte','cultura','lazer','compras','outros')",
    )
