"""Add tenant-scoped notifications and FCM device registrations.

Revision ID: 3e5f7a901234
Revises: 2d4e6f809123
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa


revision = "3e5f7a901234"
down_revision = "2d4e6f809123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notificaciones", sa.Column("empresa_id", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE notificaciones n SET empresa_id = u.empresa_id "
        "FROM users u WHERE u.id = n.user_id AND n.empresa_id IS NULL"
    )
    op.execute(
        "UPDATE notificaciones SET empresa_id = (SELECT MIN(id) FROM empresas) "
        "WHERE empresa_id IS NULL"
    )
    op.create_foreign_key(
        "fk_notificaciones_empresa_id", "notificaciones", "empresas",
        ["empresa_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_notificaciones_empresa_id", "notificaciones", ["empresa_id"])
    op.alter_column("notificaciones", "empresa_id", existing_type=sa.Integer(), nullable=False)

    op.create_table(
        "push_devices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=512), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False, server_default="android"),
        sa.Column("device_id", sa.String(length=160), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token", name="uq_push_devices_token"),
    )
    op.create_index("ix_push_devices_id", "push_devices", ["id"])
    op.create_index("ix_push_devices_empresa_id", "push_devices", ["empresa_id"])
    op.create_index("ix_push_devices_user_id", "push_devices", ["user_id"])


def downgrade() -> None:
    op.drop_table("push_devices")
    op.drop_index("ix_notificaciones_empresa_id", table_name="notificaciones")
    op.drop_constraint("fk_notificaciones_empresa_id", "notificaciones", type_="foreignkey")
    op.drop_column("notificaciones", "empresa_id")
