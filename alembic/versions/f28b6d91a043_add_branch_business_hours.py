"""add branch business hours

Revision ID: f28b6d91a043
Revises: e7a1c4b9d210
Create Date: 2026-10-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f28b6d91a043"
down_revision: Union[str, Sequence[str], None] = "e7a1c4b9d210"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("ix_sucursales_name"), table_name="sucursales")
    op.create_index(op.f("ix_sucursales_name"), "sucursales", ["name"], unique=False)
    op.create_unique_constraint(
        "uq_sucursales_empresa_nombre", "sucursales", ["empresa_id", "name"]
    )
    op.add_column(
        "sucursales",
        sa.Column("hora_apertura", sa.Time(), server_default=sa.text("'09:00:00'"), nullable=False),
    )
    op.add_column(
        "sucursales",
        sa.Column("hora_cierre", sa.Time(), server_default=sa.text("'18:00:00'"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("sucursales", "hora_cierre")
    op.drop_column("sucursales", "hora_apertura")
    op.drop_constraint("uq_sucursales_empresa_nombre", "sucursales", type_="unique")
    op.drop_index(op.f("ix_sucursales_name"), table_name="sucursales")
    op.create_index(op.f("ix_sucursales_name"), "sucursales", ["name"], unique=True)
