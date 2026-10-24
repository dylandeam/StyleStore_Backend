"""Add tenant-safe scheduled notification campaigns.

Revision ID: 5a7b9c123456
Revises: 4f6a8b012345
Create Date: 2026-10-24
"""
from alembic import op
import sqlalchemy as sa


revision = "5a7b9c123456"
down_revision = "4f6a8b012345"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campanas_notificacion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("url_accion", sa.String(300), nullable=True),
        sa.Column("audiencia", sa.String(40), nullable=False),
        sa.Column("target_user_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("target_empresa_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("enviar_email", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recurrencia_dias", sa.Integer(), nullable=True),
        sa.Column("proxima_ejecucion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="programada"),
        sa.Column("total_destinatarios", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_enviados", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ultima_ejecucion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_campanas_notificacion_empresa_id", "campanas_notificacion", ["empresa_id"])
    op.create_index("ix_campanas_notificacion_created_by_id", "campanas_notificacion", ["created_by_id"])
    op.create_index("ix_campanas_notificacion_proxima_ejecucion", "campanas_notificacion", ["proxima_ejecucion"])
    op.create_index("ix_campanas_notificacion_estado", "campanas_notificacion", ["estado"])

    op.create_table(
        "entregas_campana_notificacion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campana_id", sa.Integer(), sa.ForeignKey("campanas_notificacion.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ejecucion_programada", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "campana_id", "user_id", "empresa_id", "ejecucion_programada",
            name="uq_entrega_campana_destinatario_ejecucion",
        ),
    )
    op.create_index("ix_entregas_campana_notificacion_campana_id", "entregas_campana_notificacion", ["campana_id"])
    op.create_index("ix_entregas_campana_notificacion_user_id", "entregas_campana_notificacion", ["user_id"])
    op.create_index("ix_entregas_campana_notificacion_empresa_id", "entregas_campana_notificacion", ["empresa_id"])


def downgrade() -> None:
    op.drop_table("entregas_campana_notificacion")
    op.drop_table("campanas_notificacion")
