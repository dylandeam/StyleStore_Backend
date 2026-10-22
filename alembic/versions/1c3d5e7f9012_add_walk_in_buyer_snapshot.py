"""Add walk-in buyer snapshot to in-store sales.

Revision ID: 1c3d5e7f9012
Revises: 0b2c4d6e8f90
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = "1c3d5e7f9012"
down_revision = "0b2c4d6e8f90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("orden_venta", "codigo_cliente", existing_type=sa.String(length=30), nullable=True)
    op.add_column("orden_venta", sa.Column("comprador_nombre", sa.String(length=160), nullable=True))
    op.add_column("orden_venta", sa.Column("comprador_ci", sa.String(length=20), nullable=True))
    op.create_index("ix_orden_venta_comprador_ci", "orden_venta", ["comprador_ci"])


def downgrade() -> None:
    op.execute("DELETE FROM orden_venta WHERE codigo_cliente IS NULL")
    op.drop_index("ix_orden_venta_comprador_ci", table_name="orden_venta")
    op.drop_column("orden_venta", "comprador_ci")
    op.drop_column("orden_venta", "comprador_nombre")
    op.alter_column("orden_venta", "codigo_cliente", existing_type=sa.String(length=30), nullable=False)
