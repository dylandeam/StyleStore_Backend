"""add product reviews

Revision ID: 8d0e2f456789
Revises: 7c9d1e345678
"""
from alembic import op
import sqlalchemy as sa


revision = "8d0e2f456789"
down_revision = "7c9d1e345678"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resenas_producto",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("producto_codigo", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("puntuacion", sa.Integer(), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("puntuacion >= 1 AND puntuacion <= 5", name="ck_resena_producto_puntuacion"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["producto_codigo"], ["productos.codigo"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id", "producto_codigo", "user_id", name="uq_resena_producto_usuario"),
    )
    op.create_index(op.f("ix_resenas_producto_id"), "resenas_producto", ["id"], unique=False)
    op.create_index(op.f("ix_resenas_producto_empresa_id"), "resenas_producto", ["empresa_id"], unique=False)
    op.create_index(op.f("ix_resenas_producto_producto_codigo"), "resenas_producto", ["producto_codigo"], unique=False)
    op.create_index(op.f("ix_resenas_producto_user_id"), "resenas_producto", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_resenas_producto_user_id"), table_name="resenas_producto")
    op.drop_index(op.f("ix_resenas_producto_producto_codigo"), table_name="resenas_producto")
    op.drop_index(op.f("ix_resenas_producto_empresa_id"), table_name="resenas_producto")
    op.drop_index(op.f("ix_resenas_producto_id"), table_name="resenas_producto")
    op.drop_table("resenas_producto")
