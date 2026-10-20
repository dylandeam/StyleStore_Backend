"""add empresa tenant foundation

Revision ID: e7a1c4b9d210
Revises: d59b0f213a5b
Create Date: 2026-10-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7a1c4b9d210"
down_revision: Union[str, Sequence[str], None] = "d59b0f213a5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "empresas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_index(op.f("ix_empresas_id"), "empresas", ["id"], unique=False)
    op.create_index(op.f("ix_empresas_codigo"), "empresas", ["codigo"], unique=True)
    op.create_index(op.f("ix_empresas_nombre"), "empresas", ["nombre"], unique=True)

    op.execute("INSERT INTO empresas (codigo, nombre, active) VALUES ('stylestore', 'StyleStore', true)")

    op.add_column("users", sa.Column("empresa_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("is_platform_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.create_index(op.f("ix_users_empresa_id"), "users", ["empresa_id"], unique=False)
    op.create_foreign_key("fk_users_empresa_id", "users", "empresas", ["empresa_id"], ["id"], ondelete="RESTRICT")

    op.add_column("sucursales", sa.Column("empresa_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_sucursales_empresa_id"), "sucursales", ["empresa_id"], unique=False)
    op.create_foreign_key("fk_sucursales_empresa_id", "sucursales", "empresas", ["empresa_id"], ["id"], ondelete="RESTRICT")

    op.execute("UPDATE users SET empresa_id = (SELECT id FROM empresas WHERE codigo = 'stylestore') WHERE empresa_id IS NULL")
    op.execute("UPDATE sucursales SET empresa_id = (SELECT id FROM empresas WHERE codigo = 'stylestore') WHERE empresa_id IS NULL")
    op.execute(
        "UPDATE users SET is_platform_admin = true WHERE id = "
        "(SELECT id FROM users WHERE role = 'administrador' ORDER BY id LIMIT 1)"
    )


def downgrade() -> None:
    op.drop_constraint("fk_sucursales_empresa_id", "sucursales", type_="foreignkey")
    op.drop_index(op.f("ix_sucursales_empresa_id"), table_name="sucursales")
    op.drop_column("sucursales", "empresa_id")
    op.drop_constraint("fk_users_empresa_id", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_empresa_id"), table_name="users")
    op.drop_column("users", "is_platform_admin")
    op.drop_column("users", "empresa_id")
    op.drop_index(op.f("ix_empresas_nombre"), table_name="empresas")
    op.drop_index(op.f("ix_empresas_codigo"), table_name="empresas")
    op.drop_index(op.f("ix_empresas_id"), table_name="empresas")
    op.drop_table("empresas")
