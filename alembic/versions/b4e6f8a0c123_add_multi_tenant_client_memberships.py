"""add multi tenant client memberships

Revision ID: b4e6f8a0c123
Revises: a3d9e0f1b822
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = "b4e6f8a0c123"
down_revision = "a3d9e0f1b822"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_empresas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "empresa_id", name="uq_user_empresa"),
    )
    op.create_index("ix_user_empresas_user_id", "user_empresas", ["user_id"])
    op.create_index("ix_user_empresas_empresa_id", "user_empresas", ["empresa_id"])
    op.execute(
        "INSERT INTO user_empresas (user_id, empresa_id, active) "
        "SELECT id, empresa_id, true FROM users WHERE empresa_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_user_empresas_empresa_id", table_name="user_empresas")
    op.drop_index("ix_user_empresas_user_id", table_name="user_empresas")
    op.drop_table("user_empresas")
