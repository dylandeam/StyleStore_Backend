"""add review sync idempotency

Revision ID: a02b4c678901
Revises: 9f1a3b567890
"""
from alembic import op
import sqlalchemy as sa


revision = "a02b4c678901"
down_revision = "9f1a3b567890"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "resenas_producto",
        sa.Column("client_operation_uuid", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_resenas_producto_client_operation_uuid",
        "resenas_producto",
        ["client_operation_uuid"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_resenas_producto_client_operation_uuid", table_name="resenas_producto")
    op.drop_column("resenas_producto", "client_operation_uuid")
