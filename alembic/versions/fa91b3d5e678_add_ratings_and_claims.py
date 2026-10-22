"""Add post-purchase service ratings and claims.

Revision ID: fa91b3d5e678
Revises: f8d0a2c4e567
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa

revision = "fa91b3d5e678"
down_revision = "f8d0a2c4e567"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calificaciones_servicio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("orden_venta_id", sa.Integer(), sa.ForeignKey("orden_venta.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sucursal_id", sa.Integer(), sa.ForeignKey("sucursales.id", ondelete="SET NULL"), nullable=True),
        sa.Column("puntuacion", sa.Integer(), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "orden_venta_id", name="uq_calificacion_usuario_orden"),
        sa.CheckConstraint("puntuacion >= 1 AND puntuacion <= 5", name="ck_calificacion_puntuacion_1_5"),
    )
    for column in ("empresa_id", "user_id", "orden_venta_id", "sucursal_id"):
        op.create_index(f"ix_calificaciones_servicio_{column}", "calificaciones_servicio", [column])
    op.create_table(
        "reclamos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("orden_venta_id", sa.Integer(), sa.ForeignKey("orden_venta.id", ondelete="SET NULL"), nullable=True),
        sa.Column("calificacion_id", sa.Integer(), sa.ForeignKey("calificaciones_servicio.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sucursal_id", sa.Integer(), sa.ForeignKey("sucursales.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fecha_incidente", sa.Date(), nullable=False),
        sa.Column("motivo", sa.String(40), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False, server_default="recibido"),
        sa.Column("respuesta", sa.Text(), nullable=True),
        sa.Column("resuelto_por_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resuelto_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for column in ("empresa_id", "user_id", "orden_venta_id", "calificacion_id", "sucursal_id", "estado"):
        op.create_index(f"ix_reclamos_{column}", "reclamos", [column])


def downgrade() -> None:
    op.drop_table("reclamos")
    op.drop_table("calificaciones_servicio")

