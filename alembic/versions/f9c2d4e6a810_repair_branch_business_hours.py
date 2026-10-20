"""repair branch business hours on databases stamped before the columns existed

Revision ID: f9c2d4e6a810
Revises: c63e9a2b4d85
Create Date: 2026-10-20

This migration is intentionally defensive.  Some deployed databases reached the
current Alembic head with the branch-hours revision already stamped, but without
the two columns that the application now reads.  Fresh databases already contain
them through f28b6d91a043, so this migration becomes a no-op there.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9c2d4e6a810"
down_revision: Union[str, Sequence[str], None] = "c63e9a2b4d85"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    column_names = {column["name"] for column in inspector.get_columns("sucursales")}

    if "hora_apertura" not in column_names:
        op.add_column(
            "sucursales",
            sa.Column(
                "hora_apertura",
                sa.Time(),
                server_default=sa.text("'09:00:00'"),
                nullable=False,
            ),
        )

    if "hora_cierre" not in column_names:
        op.add_column(
            "sucursales",
            sa.Column(
                "hora_cierre",
                sa.Time(),
                server_default=sa.text("'18:00:00'"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    # These columns belong to f28b6d91a043.  Removing this repair revision must
    # not remove columns created by that original migration.
    pass
