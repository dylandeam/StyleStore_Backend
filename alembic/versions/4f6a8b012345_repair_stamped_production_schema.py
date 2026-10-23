"""Repair production schema revisions that were stamped without applying DDL.

Revision ID: 4f6a8b012345
Revises: 3e5f7a901234
Create Date: 2026-10-23

The Railway database reached the previous Alembic head while several columns from
older revisions were absent.  This migration is deliberately idempotent: a fresh
database is already complete, while a drifted database receives only the missing
columns, indexes, constraints and nullability repairs.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision = "4f6a8b012345"
down_revision = "3e5f7a901234"
branch_labels = None
depends_on = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _column(table: str, name: str) -> dict | None:
    return next(
        (item for item in _inspector().get_columns(table) if item["name"] == name),
        None,
    )


def _add_column(table: str, column: sa.Column) -> None:
    if _column(table, column.name) is None:
        op.add_column(table, column)


def _ensure_index(
    name: str, table: str, columns: Sequence[str], *, unique: bool = False
) -> None:
    inspector = _inspector()
    indexes = inspector.get_indexes(table)
    unique_constraints = inspector.get_unique_constraints(table)
    wanted = list(columns)
    if any(index["name"] == name for index in indexes):
        return
    if unique and any(item.get("column_names") == wanted for item in unique_constraints):
        return
    op.create_index(name, table, wanted, unique=unique)


def _ensure_foreign_key(
    name: str,
    source_table: str,
    target_table: str,
    source_columns: Sequence[str],
    target_columns: Sequence[str],
    *,
    ondelete: str,
) -> None:
    wanted = list(source_columns)
    foreign_keys = _inspector().get_foreign_keys(source_table)
    if any(item.get("constrained_columns") == wanted for item in foreign_keys):
        return
    op.create_foreign_key(
        name,
        source_table,
        target_table,
        wanted,
        list(target_columns),
        ondelete=ondelete,
    )


def _ensure_check(name: str, table: str, condition: str) -> None:
    if any(item.get("name") == name for item in _inspector().get_check_constraints(table)):
        return
    op.create_check_constraint(name, table, condition)


def _make_not_null(table: str, column: str, existing_type: sa.types.TypeEngine) -> None:
    current = _column(table, column)
    if current is not None and current.get("nullable", True):
        op.alter_column(table, column, existing_type=existing_type, nullable=False)


def upgrade() -> None:
    # Core tenant and scheduling fields.
    _add_column(
        "empresas",
        sa.Column("plazo_cambios_dias", sa.Integer(), nullable=False, server_default="7"),
    )
    _add_column(
        "sucursales",
        sa.Column(
            "hora_apertura",
            sa.Time(),
            nullable=False,
            server_default=sa.text("'09:00:00'"),
        ),
    )
    _add_column(
        "sucursales",
        sa.Column(
            "hora_cierre",
            sa.Time(),
            nullable=False,
            server_default=sa.text("'18:00:00'"),
        ),
    )
    _add_column(
        "empleados",
        sa.Column(
            "jornada_tipo",
            sa.String(length=20),
            nullable=False,
            server_default="tiempo_completo",
        ),
    )
    _ensure_check(
        "ck_empleados_jornada_tipo",
        "empleados",
        "jornada_tipo IN ('tiempo_completo', 'medio_tiempo')",
    )

    # Tenant ownership for resources created before multi-tenant scoping.
    for table in ("uploaded_files", "proximamente", "pruebas_virtuales"):
        _add_column(table, sa.Column("empresa_id", sa.Integer(), nullable=True))

    op.execute(
        "UPDATE uploaded_files SET empresa_id = COALESCE("
        "(SELECT id FROM empresas WHERE codigo = 'stylestore' LIMIT 1), "
        "(SELECT MIN(id) FROM empresas)) WHERE empresa_id IS NULL"
    )
    op.execute(
        "UPDATE proximamente p SET empresa_id = COALESCE("
        "(SELECT empresa_id FROM categorias WHERE id = p.categoria_id), "
        "(SELECT empresa_id FROM proveedores WHERE codigo = p.proveedor_codigo), "
        "(SELECT id FROM empresas WHERE codigo = 'stylestore' LIMIT 1), "
        "(SELECT MIN(id) FROM empresas)) WHERE empresa_id IS NULL"
    )
    op.execute(
        "UPDATE pruebas_virtuales pv SET empresa_id = COALESCE("
        "(SELECT empresa_id FROM productos WHERE codigo = pv.producto_codigo), "
        "(SELECT empresa_id FROM users WHERE id = pv.user_id), "
        "(SELECT id FROM empresas WHERE codigo = 'stylestore' LIMIT 1), "
        "(SELECT MIN(id) FROM empresas)) WHERE empresa_id IS NULL"
    )
    for table in ("uploaded_files", "proximamente", "pruebas_virtuales"):
        _ensure_foreign_key(
            f"fk_{table}_empresa_id",
            table,
            "empresas",
            ["empresa_id"],
            ["id"],
            ondelete="CASCADE",
        )
        _ensure_index(f"ix_{table}_empresa_id", table, ["empresa_id"])
        _make_not_null(table, "empresa_id", sa.Integer())

    # Offline idempotency and complete order snapshot.
    _add_column(
        "orden_venta",
        sa.Column("client_operation_uuid", sa.String(length=36), nullable=True),
    )
    _ensure_index(
        "ix_orden_venta_client_operation_uuid",
        "orden_venta",
        ["client_operation_uuid"],
        unique=True,
    )
    _add_column("orden_venta", sa.Column("subtotal_productos", sa.Numeric(10, 2), nullable=True))
    _add_column(
        "orden_venta",
        sa.Column("descuento_promociones", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    _add_column(
        "orden_venta",
        sa.Column("descuento_codigo", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    _add_column("orden_venta", sa.Column("codigo_descuento", sa.String(length=40), nullable=True))
    _add_column(
        "orden_venta",
        sa.Column("porcentaje_codigo", sa.Integer(), nullable=False, server_default="0"),
    )
    _add_column("orden_venta", sa.Column("comprador_nombre", sa.String(length=160), nullable=True))
    _add_column("orden_venta", sa.Column("comprador_ci", sa.String(length=20), nullable=True))
    _ensure_index("ix_orden_venta_comprador_ci", "orden_venta", ["comprador_ci"])
    _add_column("orden_venta", sa.Column("tipo_entrega", sa.String(length=20), nullable=True))
    _add_column("orden_venta", sa.Column("fecha_recojo", sa.Date(), nullable=True))
    _add_column("orden_venta", sa.Column("hora_recojo", sa.Time(), nullable=True))
    if not _column("orden_venta", "codigo_cliente")["nullable"]:
        op.alter_column(
            "orden_venta",
            "codigo_cliente",
            existing_type=sa.String(length=30),
            nullable=True,
        )

    # Reservation fields used by the deployed mobile/offline flows.
    _add_column(
        "reservas",
        sa.Column("client_operation_uuid", sa.String(length=36), nullable=True),
    )
    _ensure_index(
        "ix_reservas_client_operation_uuid",
        "reservas",
        ["client_operation_uuid"],
        unique=True,
    )
    _add_column(
        "reservas",
        sa.Column("tipo", sa.String(length=30), nullable=False, server_default="reserva_prenda"),
    )
    _add_column("reservas", sa.Column("orden_venta_id", sa.Integer(), nullable=True))
    _ensure_foreign_key(
        "fk_reservas_orden_venta",
        "reservas",
        "orden_venta",
        ["orden_venta_id"],
        ["id"],
        ondelete="CASCADE",
    )
    _ensure_index(
        "ix_reservas_orden_venta_id",
        "reservas",
        ["orden_venta_id"],
        unique=True,
    )

    # Exchange financial settlement.
    exchange_columns = (
        sa.Column("nuevo_stock_inventario_id", sa.Integer(), nullable=True),
        sa.Column("precio_original", sa.Numeric(10, 2), nullable=True),
        sa.Column("precio_nuevo", sa.Numeric(10, 2), nullable=True),
        sa.Column("monto_adicional", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("saldo_favor_generado", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("monto_reembolsado", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("metodo_pago_diferencia", sa.String(length=30), nullable=True),
        sa.Column("nota_venta_numero", sa.String(length=50), nullable=True),
        sa.Column("orden_ajuste_id", sa.Integer(), nullable=True),
    )
    for column in exchange_columns:
        _add_column("cambios_devolucion", column)
    _ensure_foreign_key(
        "fk_cambio_nuevo_stock",
        "cambios_devolucion",
        "stock_inventario",
        ["nuevo_stock_inventario_id"],
        ["id"],
        ondelete="SET NULL",
    )
    _ensure_foreign_key(
        "fk_cambio_orden_ajuste",
        "cambios_devolucion",
        "orden_venta",
        ["orden_ajuste_id"],
        ["id"],
        ondelete="SET NULL",
    )
    _ensure_index(
        "ix_cambio_nota_venta_numero",
        "cambios_devolucion",
        ["nota_venta_numero"],
        unique=True,
    )

    # Tenant-scoped notifications were also stamped without their owner column.
    _add_column("notificaciones", sa.Column("empresa_id", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE notificaciones n SET empresa_id = u.empresa_id "
        "FROM users u WHERE u.id = n.user_id AND n.empresa_id IS NULL"
    )
    op.execute(
        "UPDATE notificaciones SET empresa_id = (SELECT MIN(id) FROM empresas) "
        "WHERE empresa_id IS NULL"
    )
    _ensure_foreign_key(
        "fk_notificaciones_empresa_id",
        "notificaciones",
        "empresas",
        ["empresa_id"],
        ["id"],
        ondelete="CASCADE",
    )
    _ensure_index("ix_notificaciones_empresa_id", "notificaciones", ["empresa_id"])
    _make_not_null("notificaciones", "empresa_id", sa.Integer())

    # Nullability repairs for columns present in Railway but not matching models.
    op.execute("UPDATE users SET is_platform_admin = false WHERE is_platform_admin IS NULL")
    _make_not_null("users", "is_platform_admin", sa.Boolean())
    op.execute(
        "UPDATE contrataciones_plan SET estado_pago = 'pendiente' WHERE estado_pago IS NULL"
    )
    _make_not_null("contrataciones_plan", "estado_pago", sa.String(length=20))
    op.execute("UPDATE productos SET tipo_prenda = 'superior' WHERE tipo_prenda IS NULL")
    _make_not_null("productos", "tipo_prenda", sa.String(length=30))
    op.execute("UPDATE productos SET visible_en_catalogo = true WHERE visible_en_catalogo IS NULL")
    _make_not_null("productos", "visible_en_catalogo", sa.Boolean())
    op.execute("UPDATE productos SET en_promocion = false WHERE en_promocion IS NULL")
    _make_not_null("productos", "en_promocion", sa.Boolean())
    op.execute("UPDATE productos SET porcentaje_descuento = 0 WHERE porcentaje_descuento IS NULL")
    _make_not_null("productos", "porcentaje_descuento", sa.Integer())
    op.execute("UPDATE stock_inventario SET medidas = '{}' WHERE medidas IS NULL")
    _make_not_null("stock_inventario", "medidas", sa.JSON())

    op.execute(
        "UPDATE pagos AS p SET empresa_id = s.empresa_id "
        "FROM orden_venta AS o JOIN sucursales AS s ON s.id = o.sucursal_id "
        "WHERE p.orden_venta_id = o.id AND p.empresa_id IS NULL"
    )
    op.execute(
        "UPDATE pagos SET empresa_id = (SELECT MIN(id) FROM empresas) "
        "WHERE empresa_id IS NULL"
    )
    _make_not_null("pagos", "empresa_id", sa.Integer())
    _ensure_foreign_key(
        "fk_pagos_empresa_id",
        "pagos",
        "empresas",
        ["empresa_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    _ensure_index("ix_pagos_empresa_id", "pagos", ["empresa_id"])
    op.execute(
        "UPDATE pagos SET email_confirmacion_intentos = 0 "
        "WHERE email_confirmacion_intentos IS NULL"
    )
    _make_not_null("pagos", "email_confirmacion_intentos", sa.Integer())

    role_column = _column("role_permissions", "role")
    if role_column is not None and not role_column.get("nullable", True):
        op.alter_column(
            "role_permissions",
            "role",
            existing_type=sa.String(length=50),
            nullable=True,
        )


def downgrade() -> None:
    # This is a repair for columns owned by earlier revisions. Downgrading it must
    # never remove historical application data or schema elements.
    pass
