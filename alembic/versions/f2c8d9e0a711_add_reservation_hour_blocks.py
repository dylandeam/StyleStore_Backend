"""add reservation one-hour block exclusion

Revision ID: f2c8d9e0a711
Revises: e7b3c4d5a610
Create Date: 2026-10-21
"""
from alembic import op


revision = "f2c8d9e0a711"
down_revision = "e7b3c4d5a610"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_reserva_bloque_activo",
        "reservas",
        ["sucursal_id", "fecha", "hora"],
        unique=True,
        postgresql_where="estado = 'pendiente'",
        sqlite_where="estado = 'pendiente'",
    )


def downgrade() -> None:
    op.drop_index("uq_reserva_bloque_activo", table_name="reservas")
