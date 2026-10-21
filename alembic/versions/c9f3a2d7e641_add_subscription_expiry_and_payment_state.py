"""add subscription expiry and payment state

Revision ID: c9f3a2d7e641
Revises: b8e2f6041c73
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = "c9f3a2d7e641"
down_revision = "b8e2f6041c73"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    empresa_columns = {column["name"] for column in inspector.get_columns("empresas")}
    contract_columns = {
        column["name"] for column in inspector.get_columns("contrataciones_plan")
    }
    if "inactive_reason" not in empresa_columns:
        op.add_column("empresas", sa.Column("inactive_reason", sa.String(length=40), nullable=True))
    if "estado_pago" not in contract_columns:
        op.add_column(
            "contrataciones_plan",
            sa.Column("estado_pago", sa.String(length=20), server_default="pagado", nullable=False),
        )
    if "referencia_pago" not in contract_columns:
        op.add_column(
            "contrataciones_plan",
            sa.Column("referencia_pago", sa.String(length=120), nullable=True),
        )
    if "pagado_en" not in contract_columns:
        op.add_column(
            "contrataciones_plan",
            sa.Column("pagado_en", sa.DateTime(timezone=True), nullable=True),
        )
    op.execute(
        "UPDATE contrataciones_plan "
        "SET referencia_pago = 'LEGACY-' || id, pagado_en = created_at "
        "WHERE estado_pago = 'pagado'"
    )
    if bind.dialect.name != "sqlite":
        op.alter_column("contrataciones_plan", "estado_pago", server_default=None)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    empresa_columns = {column["name"] for column in inspector.get_columns("empresas")}
    contract_columns = {
        column["name"] for column in inspector.get_columns("contrataciones_plan")
    }
    if "pagado_en" in contract_columns:
        op.drop_column("contrataciones_plan", "pagado_en")
    if "referencia_pago" in contract_columns:
        op.drop_column("contrataciones_plan", "referencia_pago")
    if "estado_pago" in contract_columns:
        op.drop_column("contrataciones_plan", "estado_pago")
    if "inactive_reason" in empresa_columns:
        op.drop_column("empresas", "inactive_reason")
