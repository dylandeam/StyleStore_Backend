"""add approved quantity to inventory transfers

Revision ID: f02a5b3d8c21
Revises: e91f4a2c7b10
"""
from alembic import op
import sqlalchemy as sa


revision = "f02a5b3d8c21"
down_revision = "e91f4a2c7b10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "traspasos_inventario",
        sa.Column("cantidad_aprobada", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_traspaso_cantidad_aprobada_positiva",
        "traspasos_inventario",
        "cantidad_aprobada IS NULL OR cantidad_aprobada > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_traspaso_cantidad_aprobada_positiva",
        "traspasos_inventario",
        type_="check",
    )
    op.drop_column("traspasos_inventario", "cantidad_aprobada")
