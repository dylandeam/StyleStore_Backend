"""add offline sync operations

Revision ID: c63e9a2b4d85
Revises: b52d8f1a3c74
Create Date: 2026-10-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c63e9a2b4d85"
down_revision: Union[str, None] = "b52d8f1a3c74"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reservas", sa.Column("client_operation_uuid", sa.String(length=36), nullable=True))
    op.create_index("ix_reservas_client_operation_uuid", "reservas", ["client_operation_uuid"], unique=True)
    op.add_column("orden_venta", sa.Column("client_operation_uuid", sa.String(length=36), nullable=True))
    op.create_index("ix_orden_venta_client_operation_uuid", "orden_venta", ["client_operation_uuid"], unique=True)
    op.create_table(
        "sync_operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("operation_uuid", sa.String(length=36), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sucursal_id", sa.Integer(), nullable=True),
        sa.Column("operation_type", sa.String(length=30), nullable=False),
        sa.Column("payload_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("client_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="procesando"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("result_type", sa.String(length=30), nullable=True),
        sa.Column("result_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursales.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("operation_uuid", name="uq_sync_operation_uuid"),
    )
    op.create_index("ix_sync_operations_operation_uuid", "sync_operations", ["operation_uuid"])
    op.create_index("ix_sync_operations_empresa_id", "sync_operations", ["empresa_id"])
    op.create_index("ix_sync_operations_user_id", "sync_operations", ["user_id"])
    op.create_index("ix_sync_operations_sucursal_id", "sync_operations", ["sucursal_id"])
    op.create_index("ix_sync_operations_status", "sync_operations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_sync_operations_status", table_name="sync_operations")
    op.drop_index("ix_sync_operations_sucursal_id", table_name="sync_operations")
    op.drop_index("ix_sync_operations_user_id", table_name="sync_operations")
    op.drop_index("ix_sync_operations_empresa_id", table_name="sync_operations")
    op.drop_index("ix_sync_operations_operation_uuid", table_name="sync_operations")
    op.drop_table("sync_operations")
    op.drop_index("ix_orden_venta_client_operation_uuid", table_name="orden_venta")
    op.drop_column("orden_venta", "client_operation_uuid")
    op.drop_index("ix_reservas_client_operation_uuid", table_name="reservas")
    op.drop_column("reservas", "client_operation_uuid")
