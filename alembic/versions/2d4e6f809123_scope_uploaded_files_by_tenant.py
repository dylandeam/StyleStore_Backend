"""Scope secondary files, upcoming items and virtual try-ons by tenant.

Revision ID: 2d4e6f809123
Revises: 1c3d5e7f9012
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = "2d4e6f809123"
down_revision = "1c3d5e7f9012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("uploaded_files"):
        op.create_table(
            "uploaded_files",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("filename", sa.String(length=120), nullable=False),
            sa.Column("folder", sa.String(length=50), nullable=False),
            sa.Column("content_type", sa.String(length=80), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("data", sa.LargeBinary(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], name="fk_uploaded_files_empresa_id", ondelete="CASCADE"),
        )
        op.create_index("ix_uploaded_files_filename", "uploaded_files", ["filename"])
        op.create_index("ix_uploaded_files_folder", "uploaded_files", ["folder"])
        op.create_index("ix_uploaded_files_empresa_id", "uploaded_files", ["empresa_id"])
    else:
        op.add_column("uploaded_files", sa.Column("empresa_id", sa.Integer(), nullable=True))
        op.execute(
            "UPDATE uploaded_files SET empresa_id = COALESCE("
            "(SELECT id FROM empresas WHERE codigo = 'stylestore' LIMIT 1), "
            "(SELECT MIN(id) FROM empresas)) WHERE empresa_id IS NULL"
        )
        op.create_foreign_key(
            "fk_uploaded_files_empresa_id", "uploaded_files", "empresas",
            ["empresa_id"], ["id"], ondelete="CASCADE",
        )
        op.create_index("ix_uploaded_files_empresa_id", "uploaded_files", ["empresa_id"])
        op.alter_column("uploaded_files", "empresa_id", existing_type=sa.Integer(), nullable=False)

    op.add_column("proximamente", sa.Column("empresa_id", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE proximamente p SET empresa_id = COALESCE("
        "(SELECT empresa_id FROM categorias WHERE id = p.categoria_id), "
        "(SELECT empresa_id FROM proveedores WHERE codigo = p.proveedor_codigo), "
        "(SELECT id FROM empresas WHERE codigo = 'stylestore' LIMIT 1), "
        "(SELECT MIN(id) FROM empresas)) WHERE empresa_id IS NULL"
    )
    op.create_foreign_key(
        "fk_proximamente_empresa_id", "proximamente", "empresas",
        ["empresa_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_proximamente_empresa_id", "proximamente", ["empresa_id"])
    op.alter_column("proximamente", "empresa_id", existing_type=sa.Integer(), nullable=False)

    if not inspector.has_table("pruebas_virtuales"):
        op.create_table(
            "pruebas_virtuales",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("producto_codigo", sa.String(length=50), nullable=False),
            sa.Column("foto_persona_url", sa.String(length=500), nullable=False),
            sa.Column("foto_resultado_url", sa.String(length=500), nullable=True),
            sa.Column("estado", sa.String(length=20), nullable=False, server_default="procesando"),
            sa.Column("mensaje_error", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], name="fk_pruebas_virtuales_empresa_id", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_pruebas_virtuales_user_id", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["producto_codigo"], ["productos.codigo"], name="fk_pruebas_virtuales_producto_codigo", ondelete="CASCADE"),
        )
        op.create_index("ix_pruebas_virtuales_id", "pruebas_virtuales", ["id"])
        op.create_index("ix_pruebas_virtuales_empresa_id", "pruebas_virtuales", ["empresa_id"])
    else:
        op.add_column("pruebas_virtuales", sa.Column("empresa_id", sa.Integer(), nullable=True))
        op.execute(
            "UPDATE pruebas_virtuales pv SET empresa_id = COALESCE("
            "(SELECT empresa_id FROM productos WHERE codigo = pv.producto_codigo), "
            "(SELECT empresa_id FROM users WHERE id = pv.user_id), "
            "(SELECT id FROM empresas WHERE codigo = 'stylestore' LIMIT 1), "
            "(SELECT MIN(id) FROM empresas)) WHERE empresa_id IS NULL"
        )
        op.create_foreign_key(
            "fk_pruebas_virtuales_empresa_id", "pruebas_virtuales", "empresas",
            ["empresa_id"], ["id"], ondelete="CASCADE",
        )
        op.create_index("ix_pruebas_virtuales_empresa_id", "pruebas_virtuales", ["empresa_id"])
        op.alter_column("pruebas_virtuales", "empresa_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.drop_index("ix_pruebas_virtuales_empresa_id", table_name="pruebas_virtuales")
    op.drop_constraint("fk_pruebas_virtuales_empresa_id", "pruebas_virtuales", type_="foreignkey")
    op.drop_column("pruebas_virtuales", "empresa_id")
    op.drop_index("ix_proximamente_empresa_id", table_name="proximamente")
    op.drop_constraint("fk_proximamente_empresa_id", "proximamente", type_="foreignkey")
    op.drop_column("proximamente", "empresa_id")
    op.drop_index("ix_uploaded_files_empresa_id", table_name="uploaded_files")
    op.drop_constraint("fk_uploaded_files_empresa_id", "uploaded_files", type_="foreignkey")
    op.drop_column("uploaded_files", "empresa_id")
