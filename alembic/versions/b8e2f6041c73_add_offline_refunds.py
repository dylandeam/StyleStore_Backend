"""add auditable offline cash refunds

Revision ID: b8e2f6041c73
Revises: a7d1e5f903b2
Create Date: 2026-10-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b8e2f6041c73"
down_revision: Union[str, Sequence[str], None] = "a7d1e5f903b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reembolsos_offline",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sucursal_id", sa.Integer(), sa.ForeignKey("sucursales.id", ondelete="SET NULL")),
        sa.Column("sync_operation_id", sa.Integer(), sa.ForeignKey("sync_operations.id", ondelete="RESTRICT"), unique=True, nullable=False),
        sa.Column("operation_uuid", sa.String(36), unique=True, nullable=False),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="BOB"),
        sa.Column("metodo_original", sa.String(30), nullable=False, server_default="efectivo"),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente"),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("observaciones", sa.Text()),
        sa.Column("procesado_por", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("procesado_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_reembolsos_offline_empresa_id", "reembolsos_offline", ["empresa_id"])
    op.create_index("ix_reembolsos_offline_user_id", "reembolsos_offline", ["user_id"])
    op.create_index("ix_reembolsos_offline_estado", "reembolsos_offline", ["estado"])


def downgrade() -> None:
    op.drop_table("reembolsos_offline")
