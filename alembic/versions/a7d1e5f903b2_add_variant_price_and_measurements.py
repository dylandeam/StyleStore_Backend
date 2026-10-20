"""add price and garment measurements per inventory variant

Revision ID: a7d1e5f903b2
Revises: f9c2d4e6a810
Create Date: 2026-10-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7d1e5f903b2"
down_revision: Union[str, Sequence[str], None] = "f9c2d4e6a810"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stock_inventario", sa.Column("precio_variante", sa.Numeric(12, 2), nullable=True))
    op.add_column(
        "stock_inventario",
        sa.Column("medidas", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("stock_inventario", "medidas")
    op.drop_column("stock_inventario", "precio_variante")
