"""Add tenant-scoped product favorites.

Revision ID: f8d0a2c4e567
Revises: e7b9c1d3f456
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa

revision = "f8d0a2c4e567"
down_revision = "e7b9c1d3f456"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "favoritos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("producto_codigo", sa.String(50), sa.ForeignKey("productos.codigo", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "empresa_id", "producto_codigo", name="uq_favorito_usuario_empresa_producto"),
    )
    op.create_index("ix_favoritos_user_id", "favoritos", ["user_id"])
    op.create_index("ix_favoritos_empresa_id", "favoritos", ["empresa_id"])
    op.create_index("ix_favoritos_producto_codigo", "favoritos", ["producto_codigo"])


def downgrade() -> None:
    op.drop_index("ix_favoritos_producto_codigo", table_name="favoritos")
    op.drop_index("ix_favoritos_empresa_id", table_name="favoritos")
    op.drop_index("ix_favoritos_user_id", table_name="favoritos")
    op.drop_table("favoritos")

