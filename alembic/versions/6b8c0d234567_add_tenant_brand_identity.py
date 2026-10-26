"""Add configurable brand identity to tenants.

Revision ID: 6b8c0d234567
Revises: 5a7b9c123456
Create Date: 2026-10-26
"""
from alembic import op
import sqlalchemy as sa


revision = "6b8c0d234567"
down_revision = "5a7b9c123456"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("empresas", sa.Column("nombre_marca", sa.String(150), nullable=True))
    op.add_column("empresas", sa.Column("eslogan", sa.String(220), nullable=True))
    op.add_column("empresas", sa.Column("logo_url", sa.String(500), nullable=True))
    op.add_column("empresas", sa.Column("color_primario", sa.String(7), nullable=False, server_default="#14263D"))
    op.add_column("empresas", sa.Column("color_secundario", sa.String(7), nullable=False, server_default="#FBF8F1"))
    op.add_column("empresas", sa.Column("color_acento", sa.String(7), nullable=False, server_default="#274C77"))
    op.add_column("empresas", sa.Column("color_fondo", sa.String(7), nullable=False, server_default="#EEE7D8"))
    op.add_column("empresas", sa.Column("color_texto", sa.String(7), nullable=False, server_default="#172536"))


def downgrade() -> None:
    for column in (
        "color_texto", "color_fondo", "color_acento", "color_secundario",
        "color_primario", "logo_url", "eslogan", "nombre_marca",
    ):
        op.drop_column("empresas", column)
