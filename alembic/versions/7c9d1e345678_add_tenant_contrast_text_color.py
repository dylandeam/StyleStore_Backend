"""Add tenant text color for contrast surfaces.

Revision ID: 7c9d1e345678
Revises: 6b8c0d234567
Create Date: 2026-10-26
"""
from alembic import op
import sqlalchemy as sa


revision = "7c9d1e345678"
down_revision = "6b8c0d234567"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresas",
        sa.Column(
            "color_texto_contraste",
            sa.String(7),
            nullable=False,
            server_default="#FFFFFF",
        ),
    )


def downgrade() -> None:
    op.drop_column("empresas", "color_texto_contraste")
