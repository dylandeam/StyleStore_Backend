"""scope roles and permissions by tenant

Revision ID: b13c5d789012
Revises: a02b4c678901
"""
from alembic import op
import sqlalchemy as sa


revision = "b13c5d789012"
down_revision = "a02b4c678901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("roles", sa.Column("empresa_id", sa.Integer(), nullable=True))
    op.create_index("ix_roles_empresa_id", "roles", ["empresa_id"], unique=False)
    op.create_foreign_key(
        "fk_roles_empresa_id_empresas",
        "roles",
        "empresas",
        ["empresa_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_index("ix_roles_nombre", table_name="roles")
    op.create_unique_constraint("uq_roles_empresa_nombre", "roles", ["empresa_id", "nombre"])

    # Existing global roles become templates. Each tenant receives an isolated copy
    # together with the current permission matrix, and its users are relinked.
    bind = op.get_bind()
    empresas = bind.execute(sa.text("SELECT id FROM empresas ORDER BY id")).fetchall()
    templates = bind.execute(
        sa.text("SELECT id, nombre, descripcion, active FROM roles WHERE empresa_id IS NULL ORDER BY id")
    ).fetchall()
    for (empresa_id,) in empresas:
        for template_id, nombre, descripcion, active in templates:
            new_role_id = bind.execute(
                sa.text(
                    """
                    INSERT INTO roles (empresa_id, nombre, descripcion, active, created_at, updated_at)
                    VALUES (:empresa_id, :nombre, :descripcion, :active, NOW(), NOW())
                    RETURNING id
                    """
                ),
                {
                    "empresa_id": empresa_id,
                    "nombre": nombre,
                    "descripcion": descripcion,
                    "active": active,
                },
            ).scalar_one()
            bind.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role, role_id, permission_id)
                    SELECT role, :new_role_id, permission_id
                    FROM role_permissions
                    WHERE role_id = :template_id
                    """
                ),
                {"new_role_id": new_role_id, "template_id": template_id},
            )
            slug = str(nombre).lower().replace(" ", "_")
            legacy_slug = "encargado_sucursal" if slug == "encargado_de_sucursal" else slug
            bind.execute(
                sa.text(
                    """
                    UPDATE users
                    SET role_id = :new_role_id
                    WHERE empresa_id = :empresa_id
                      AND (role_id = :template_id OR lower(role) IN (:slug, :legacy_slug))
                    """
                ),
                {
                    "new_role_id": new_role_id,
                    "empresa_id": empresa_id,
                    "template_id": template_id,
                    "slug": slug,
                    "legacy_slug": legacy_slug,
                },
            )

    operational_permissions = [
        ("carrito.usar", "carrito", "Agregar, modificar y quitar prendas del carrito"),
        ("ventas.crear", "ventas", "Registrar ventas presenciales y cobros de mostrador"),
        ("ventas.comprar", "ventas", "Confirmar compras y procesar pagos como cliente"),
        ("resenas.crear", "resenas", "Publicar, editar o eliminar reseñas de productos"),
    ]
    for code, module, description in operational_permissions:
        bind.execute(
            sa.text(
                """
                INSERT INTO permissions (code, module, description)
                VALUES (:code, :module, :description)
                ON CONFLICT (code) DO UPDATE
                SET module = EXCLUDED.module, description = EXCLUDED.description
                """
            ),
            {"code": code, "module": module, "description": description},
        )

    assignments = {
        "Administrador": [code for code, _, _ in operational_permissions],
        "Encargado de Sucursal": ["ventas.crear"],
        "Cajero": ["ventas.crear"],
        "Cliente": ["carrito.usar", "ventas.comprar", "resenas.crear"],
    }
    for role_name, codes in assignments.items():
        for code in codes:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role, role_id, permission_id)
                    SELECT lower(replace(r.nombre, ' ', '_')), r.id, p.id
                    FROM roles r
                    JOIN permissions p ON p.code = :code
                    WHERE r.empresa_id IS NOT NULL AND lower(r.nombre) = lower(:role_name)
                      AND NOT EXISTS (
                        SELECT 1 FROM role_permissions rp
                        WHERE rp.role_id = r.id AND rp.permission_id = p.id
                      )
                    """
                ),
                {"code": code, "role_name": role_name},
            )


def downgrade() -> None:
    # Keep one role per name and relink users before restoring the legacy unique key.
    bind = op.get_bind()
    template_rows = bind.execute(
        sa.text("SELECT id, nombre FROM roles WHERE empresa_id IS NULL ORDER BY id")
    ).fetchall()
    for template_id, nombre in template_rows:
        bind.execute(
            sa.text(
                """
                UPDATE users u
                SET role_id = :template_id
                FROM roles r
                WHERE u.role_id = r.id AND r.empresa_id IS NOT NULL AND lower(r.nombre) = lower(:nombre)
                """
            ),
            {"template_id": template_id, "nombre": nombre},
        )
    bind.execute(sa.text("DELETE FROM roles WHERE empresa_id IS NOT NULL"))
    op.drop_constraint("uq_roles_empresa_nombre", "roles", type_="unique")
    op.create_index("ix_roles_nombre", "roles", ["nombre"], unique=True)
    op.drop_constraint("fk_roles_empresa_id_empresas", "roles", type_="foreignkey")
    op.drop_index("ix_roles_empresa_id", table_name="roles")
    op.drop_column("roles", "empresa_id")
