"""paypal reconciliation and automatic stock refunds

Revision ID: c24d7e890123
Revises: b13c5d789012
"""
from alembic import op
import sqlalchemy as sa

revision = "c24d7e890123"
down_revision = "b13c5d789012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orden_venta", sa.Column("inventario_descontado", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("pagos", sa.Column("operation_uuid", sa.String(length=36), nullable=True))
    op.add_column("pagos", sa.Column("paypal_refund_id", sa.String(length=100), nullable=True))
    op.add_column("pagos", sa.Column("refund_reason", sa.Text(), nullable=True))
    op.add_column("pagos", sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_pagos_operation_uuid", "pagos", ["operation_uuid"], unique=True)
    op.create_index("ix_pagos_paypal_refund_id", "pagos", ["paypal_refund_id"])


def downgrade() -> None:
    op.drop_index("ix_pagos_paypal_refund_id", table_name="pagos")
    op.drop_index("ix_pagos_operation_uuid", table_name="pagos")
    op.drop_column("pagos", "refunded_at")
    op.drop_column("pagos", "refund_reason")
    op.drop_column("pagos", "paypal_refund_id")
    op.drop_column("pagos", "operation_uuid")
    op.drop_column("orden_venta", "inventario_descontado")
