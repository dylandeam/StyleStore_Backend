"""add exchange cashier preparation state

Revision ID: e91f4a2c7b10
Revises: d35e8f901234
"""
from alembic import op
import sqlalchemy as sa


revision = "e91f4a2c7b10"
down_revision = "d35e8f901234"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cambios_devolucion",
        sa.Column("reponer_prenda_original", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("cambios_devolucion", "reponer_prenda_original")
