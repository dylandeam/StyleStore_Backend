"""scope catalog master names by tenant

Revision ID: d35e8f901234
Revises: c24d7e890123
"""
from alembic import op


revision = "d35e8f901234"
down_revision = "c24d7e890123"
branch_labels = None
depends_on = None


TABLES = ("categorias", "colores", "tallas", "temporadas")


def upgrade() -> None:
    for table in TABLES:
        op.drop_index(f"ix_{table}_nombre", table_name=table)
        op.create_index(f"ix_{table}_nombre", table, ["nombre"], unique=False)
        op.create_unique_constraint(
            f"uq_{table}_empresa_nombre", table, ["empresa_id", "nombre"]
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_constraint(f"uq_{table}_empresa_nombre", table_name=table, type_="unique")
        op.drop_index(f"ix_{table}_nombre", table_name=table)
        op.create_index(f"ix_{table}_nombre", table, ["nombre"], unique=True)
