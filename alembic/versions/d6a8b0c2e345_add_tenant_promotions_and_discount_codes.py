"""Add tenant grouped promotions and discount codes.

Revision ID: d6a8b0c2e345
Revises: c5f7a9b1d234
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa

revision = "d6a8b0c2e345"
down_revision = "c5f7a9b1d234"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "promociones_agrupadas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("categoria_id", sa.Integer(), sa.ForeignKey("categorias.id", ondelete="CASCADE"), nullable=True),
        sa.Column("temporada_id", sa.Integer(), sa.ForeignKey("temporadas.id", ondelete="CASCADE"), nullable=True),
        sa.Column("porcentaje", sa.Integer(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=True),
        sa.Column("fecha_fin", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("porcentaje BETWEEN 1 AND 90", name="ck_promocion_agrupada_porcentaje"),
        sa.CheckConstraint("(tipo = 'categoria' AND categoria_id IS NOT NULL AND temporada_id IS NULL) OR (tipo = 'temporada' AND temporada_id IS NOT NULL AND categoria_id IS NULL)", name="ck_promocion_agrupada_objetivo"),
    )
    op.create_index("ix_promociones_agrupadas_empresa_id", "promociones_agrupadas", ["empresa_id"])
    op.create_index("ix_promociones_agrupadas_categoria_id", "promociones_agrupadas", ["categoria_id"])
    op.create_index("ix_promociones_agrupadas_temporada_id", "promociones_agrupadas", ["temporada_id"])
    op.create_table(
        "codigos_descuento",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("codigo", sa.String(40), nullable=False),
        sa.Column("descripcion", sa.String(200), nullable=True),
        sa.Column("porcentaje", sa.Integer(), nullable=False),
        sa.Column("aplica_online", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("aplica_presencial", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("fecha_inicio", sa.Date(), nullable=True),
        sa.Column("fecha_fin", sa.Date(), nullable=True),
        sa.Column("max_usos", sa.Integer(), nullable=True),
        sa.Column("usos_actual", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("empresa_id", "codigo", name="uq_codigo_descuento_empresa_codigo"),
        sa.CheckConstraint("porcentaje BETWEEN 1 AND 90", name="ck_codigo_descuento_porcentaje"),
        sa.CheckConstraint("max_usos IS NULL OR max_usos > 0", name="ck_codigo_descuento_max_usos"),
    )
    op.create_index("ix_codigos_descuento_empresa_id", "codigos_descuento", ["empresa_id"])
    op.add_column("orden_venta", sa.Column("subtotal_productos", sa.Numeric(10, 2), nullable=True))
    op.add_column("orden_venta", sa.Column("descuento_promociones", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("orden_venta", sa.Column("descuento_codigo", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("orden_venta", sa.Column("codigo_descuento", sa.String(40), nullable=True))
    op.add_column("orden_venta", sa.Column("porcentaje_codigo", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    for column in ("porcentaje_codigo", "codigo_descuento", "descuento_codigo", "descuento_promociones", "subtotal_productos"):
        op.drop_column("orden_venta", column)
    op.drop_index("ix_codigos_descuento_empresa_id", table_name="codigos_descuento")
    op.drop_table("codigos_descuento")
    op.drop_index("ix_promociones_agrupadas_temporada_id", table_name="promociones_agrupadas")
    op.drop_index("ix_promociones_agrupadas_categoria_id", table_name="promociones_agrupadas")
    op.drop_index("ix_promociones_agrupadas_empresa_id", table_name="promociones_agrupadas")
    op.drop_table("promociones_agrupadas")
