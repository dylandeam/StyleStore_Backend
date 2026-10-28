"""add product size prices

Revision ID: 9f1a3b567890
Revises: 8d0e2f456789
"""
from alembic import op
import sqlalchemy as sa


revision = "9f1a3b567890"
down_revision = "8d0e2f456789"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "producto_talla_precios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("producto_codigo", sa.String(length=50), nullable=False),
        sa.Column("talla_id", sa.Integer(), nullable=False),
        sa.Column("precio", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("precio > 0", name="ck_producto_talla_precio_positivo"),
        sa.ForeignKeyConstraint(["producto_codigo"], ["productos.codigo"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["talla_id"], ["tallas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("producto_codigo", "talla_id", name="uq_producto_talla_precio"),
    )
    op.create_index(op.f("ix_producto_talla_precios_id"), "producto_talla_precios", ["id"], unique=False)
    op.create_index(op.f("ix_producto_talla_precios_producto_codigo"), "producto_talla_precios", ["producto_codigo"], unique=False)
    op.create_index(op.f("ix_producto_talla_precios_talla_id"), "producto_talla_precios", ["talla_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_producto_talla_precios_talla_id"), table_name="producto_talla_precios")
    op.drop_index(op.f("ix_producto_talla_precios_producto_codigo"), table_name="producto_talla_precios")
    op.drop_index(op.f("ix_producto_talla_precios_id"), table_name="producto_talla_precios")
    op.drop_table("producto_talla_precios")
