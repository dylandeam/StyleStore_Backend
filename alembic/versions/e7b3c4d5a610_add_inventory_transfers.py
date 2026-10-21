"""add inventory transfers

Revision ID: e7b3c4d5a610
Revises: d4a8c1f9b520
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = "e7b3c4d5a610"
down_revision = "d4a8c1f9b520"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "traspasos_inventario",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("sucursal_origen_id", sa.Integer(), nullable=False),
        sa.Column("sucursal_destino_id", sa.Integer(), nullable=False),
        sa.Column("producto_color_id", sa.Integer(), nullable=False),
        sa.Column("talla_id", sa.Integer(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=20), server_default="pendiente", nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("observacion", sa.String(length=500), nullable=True),
        sa.Column("respuesta", sa.String(length=500), nullable=True),
        sa.Column("solicitado_por_id", sa.Integer(), nullable=False),
        sa.Column("procesado_por_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("procesado_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("cantidad > 0", name="ck_traspaso_cantidad_positiva"),
        sa.CheckConstraint("sucursal_origen_id <> sucursal_destino_id", name="ck_traspaso_sucursales_distintas"),
        sa.CheckConstraint(
            "estado IN ('pendiente', 'aprobado', 'rechazado', 'cancelado')",
            name="ck_traspaso_estado",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sucursal_origen_id"], ["sucursales.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sucursal_destino_id"], ["sucursales.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["producto_color_id"], ["producto_colores.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["talla_id"], ["tallas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["solicitado_por_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["procesado_por_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id", "idempotency_key", name="uq_traspaso_empresa_idempotency"),
    )
    for column in (
        "id", "empresa_id", "sucursal_origen_id", "sucursal_destino_id",
        "producto_color_id", "talla_id", "estado", "solicitado_por_id",
    ):
        op.create_index(f"ix_traspasos_inventario_{column}", "traspasos_inventario", [column])


def downgrade() -> None:
    op.drop_table("traspasos_inventario")
