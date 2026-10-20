"""add configurable subscription plans

Revision ID: b52d8f1a3c74
Revises: a41c7e9d2b65
Create Date: 2026-10-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b52d8f1a3c74"
down_revision: Union[str, None] = "a41c7e9d2b65"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "planes_suscripcion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), nullable=True),
        sa.Column("scope_key", sa.String(length=80), nullable=False),
        sa.Column("codigo", sa.String(length=30), nullable=False),
        sa.Column("nombre", sa.String(length=80), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("precio_mensual", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("moneda", sa.String(length=3), nullable=False, server_default="BOB"),
        sa.Column("max_sucursales", sa.Integer(), nullable=True),
        sa.Column("ia_generativa", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("beneficios", sa.JSON(), nullable=False),
        sa.Column("capacidades", sa.JSON(), nullable=False),
        sa.Column("estilo", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("scope_key", "codigo", name="uq_planes_scope_codigo"),
    )
    op.create_index("ix_planes_suscripcion_empresa_id", "planes_suscripcion", ["empresa_id"])
    op.create_index("ix_planes_suscripcion_scope_key", "planes_suscripcion", ["scope_key"])

    common_false = '{"productos": true, "ventas": true, "reservas": true, "offline": true, "reportes": true, "ia_generativa": false}'
    common_true = '{"productos": true, "ventas": true, "reservas": true, "offline": true, "reportes": true, "ia_generativa": true}'
    op.execute(sa.text(f"""
        INSERT INTO planes_suscripcion
            (empresa_id, scope_key, codigo, nombre, precio_mensual, moneda,
             max_sucursales, ia_generativa, beneficios, capacidades, estilo, active)
        VALUES
            (NULL, 'global', 'basico', 'Básico', 0, 'BOB', 2, FALSE,
             CAST('[]' AS JSON), CAST('{common_false}' AS JSON), CAST('{{}}' AS JSON), TRUE),
            (NULL, 'global', 'profesional', 'Profesional', 0, 'BOB', 10, TRUE,
             CAST('[]' AS JSON), CAST('{common_true}' AS JSON), CAST('{{}}' AS JSON), TRUE),
            (NULL, 'global', 'personalizado', 'Personalizado', 0, 'BOB', NULL, FALSE,
             CAST('[]' AS JSON), CAST('{{}}' AS JSON), CAST('{{}}' AS JSON), TRUE)
    """))

    op.create_table(
        "contrataciones_plan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="activa"),
        sa.Column("precio_snapshot", sa.Numeric(12, 2), nullable=False),
        sa.Column("moneda_snapshot", sa.String(length=3), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["planes_suscripcion.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_contrataciones_plan_empresa_id", "contrataciones_plan", ["empresa_id"])
    op.create_index("ix_contrataciones_plan_user_id", "contrataciones_plan", ["user_id"])
    op.create_index("ix_contrataciones_plan_plan_id", "contrataciones_plan", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_contrataciones_plan_plan_id", table_name="contrataciones_plan")
    op.drop_index("ix_contrataciones_plan_user_id", table_name="contrataciones_plan")
    op.drop_index("ix_contrataciones_plan_empresa_id", table_name="contrataciones_plan")
    op.drop_table("contrataciones_plan")
    op.drop_index("ix_planes_suscripcion_scope_key", table_name="planes_suscripcion")
    op.drop_index("ix_planes_suscripcion_empresa_id", table_name="planes_suscripcion")
    op.drop_table("planes_suscripcion")
