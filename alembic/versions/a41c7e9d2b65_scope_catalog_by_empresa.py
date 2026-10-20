"""scope catalog by empresa

Revision ID: a41c7e9d2b65
Revises: f28b6d91a043
Create Date: 2026-10-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a41c7e9d2b65"
down_revision: Union[str, Sequence[str], None] = "f28b6d91a043"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = ("categorias", "colores", "tallas", "temporadas", "colecciones", "productos", "proveedores", "qr_pago_config", "bitacora")
NAMED_TABLES = ("categorias", "colores", "tallas", "temporadas", "colecciones")


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.add_column(table, sa.Column("empresa_id", sa.Integer(), nullable=True))
        op.create_index(op.f(f"ix_{table}_empresa_id"), table, ["empresa_id"], unique=False)
        op.create_foreign_key(
            f"fk_{table}_empresa_id", table, "empresas", ["empresa_id"], ["id"], ondelete="RESTRICT"
        )
        op.execute(
            f"UPDATE {table} SET empresa_id = (SELECT id FROM empresas WHERE codigo = 'stylestore') "
            "WHERE empresa_id IS NULL"
        )

    for table in NAMED_TABLES:
        op.drop_index(op.f(f"ix_{table}_nombre"), table_name=table)
        op.create_index(op.f(f"ix_{table}_nombre"), table, ["nombre"], unique=False)
        op.create_unique_constraint(f"uq_{table}_empresa_nombre", table, ["empresa_id", "nombre"])


def downgrade() -> None:
    for table in reversed(NAMED_TABLES):
        op.drop_constraint(f"uq_{table}_empresa_nombre", table, type_="unique")
        op.drop_index(op.f(f"ix_{table}_nombre"), table_name=table)
        op.create_index(op.f(f"ix_{table}_nombre"), table, ["nombre"], unique=True)

    for table in reversed(TENANT_TABLES):
        op.drop_constraint(f"fk_{table}_empresa_id", table, type_="foreignkey")
        op.drop_index(op.f(f"ix_{table}_empresa_id"), table_name=table)
        op.drop_column(table, "empresa_id")
