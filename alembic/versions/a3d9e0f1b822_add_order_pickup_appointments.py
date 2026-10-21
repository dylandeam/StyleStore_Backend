"""add order pickup appointments

Revision ID: a3d9e0f1b822
Revises: f2c8d9e0a711
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = "a3d9e0f1b822"
down_revision = "f2c8d9e0a711"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orden_venta", sa.Column("tipo_entrega", sa.String(20), nullable=True))
    op.add_column("orden_venta", sa.Column("fecha_recojo", sa.Date(), nullable=True))
    op.add_column("orden_venta", sa.Column("hora_recojo", sa.Time(), nullable=True))
    op.add_column("reservas", sa.Column("tipo", sa.String(30), server_default="reserva_prenda", nullable=False))
    op.add_column("reservas", sa.Column("orden_venta_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_reservas_orden_venta", "reservas", "orden_venta", ["orden_venta_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_reservas_orden_venta_id", "reservas", ["orden_venta_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_reservas_orden_venta_id", table_name="reservas")
    op.drop_constraint("fk_reservas_orden_venta", "reservas", type_="foreignkey")
    op.drop_column("reservas", "orden_venta_id")
    op.drop_column("reservas", "tipo")
    op.drop_column("orden_venta", "hora_recojo")
    op.drop_column("orden_venta", "fecha_recojo")
    op.drop_column("orden_venta", "tipo_entrega")
