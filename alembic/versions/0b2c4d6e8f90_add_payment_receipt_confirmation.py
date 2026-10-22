"""Add tenant payment receipts and idempotent confirmation delivery.

Revision ID: 0b2c4d6e8f90
Revises: fa91b3d5e678
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = "0b2c4d6e8f90"
down_revision = "fa91b3d5e678"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pagos", sa.Column("empresa_id", sa.Integer(), nullable=True))
    op.add_column("pagos", sa.Column("recibo_numero", sa.String(length=40), nullable=True))
    op.add_column("pagos", sa.Column("email_confirmacion_enviado_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pagos", sa.Column("email_confirmacion_intentos", sa.Integer(), server_default="0", nullable=False))
    op.create_foreign_key("fk_pagos_empresa_id", "pagos", "empresas", ["empresa_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_pagos_empresa_id", "pagos", ["empresa_id"])
    op.create_index("ix_pagos_recibo_numero", "pagos", ["recibo_numero"], unique=True)

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("notificaciones"):
        op.create_table(
            "notificaciones",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tipo", sa.String(50), nullable=False, server_default="general"),
            sa.Column("titulo", sa.String(200), nullable=False),
            sa.Column("mensaje", sa.Text(), nullable=False),
            sa.Column("leida", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("url_accion", sa.String(300), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_notificaciones_user_id", "notificaciones", ["user_id"])
    op.add_column("notificaciones", sa.Column("pago_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_notificaciones_pago_id", "notificaciones", "pagos", ["pago_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_notificaciones_pago_id", "notificaciones", ["pago_id"], unique=True)

    op.execute("""
        UPDATE pagos AS p
        SET empresa_id = s.empresa_id
        FROM orden_venta AS o
        JOIN sucursales AS s ON s.id = o.sucursal_id
        WHERE p.orden_venta_id = o.id AND p.empresa_id IS NULL
    """)
    op.execute("""
        UPDATE pagos
        SET empresa_id = (SELECT id FROM empresas ORDER BY id LIMIT 1)
        WHERE empresa_id IS NULL
    """)
    op.alter_column("pagos", "empresa_id", nullable=False)
    op.execute("""
        UPDATE pagos
        SET recibo_numero = 'REC-' || LPAD(id::text, 8, '0')
        WHERE estado = 'aprobado' AND recibo_numero IS NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_notificaciones_pago_id", table_name="notificaciones")
    op.drop_constraint("fk_notificaciones_pago_id", "notificaciones", type_="foreignkey")
    op.drop_column("notificaciones", "pago_id")
    op.drop_index("ix_pagos_recibo_numero", table_name="pagos")
    op.drop_index("ix_pagos_empresa_id", table_name="pagos")
    op.drop_constraint("fk_pagos_empresa_id", "pagos", type_="foreignkey")
    op.drop_column("pagos", "email_confirmacion_intentos")
    op.drop_column("pagos", "email_confirmacion_enviado_at")
    op.drop_column("pagos", "recibo_numero")
    op.drop_column("pagos", "empresa_id")
