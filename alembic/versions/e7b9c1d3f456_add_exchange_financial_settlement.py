"""Add configurable exchange policy and financial settlement.

Revision ID: e7b9c1d3f456
Revises: d6a8b0c2e345
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa

revision = "e7b9c1d3f456"
down_revision = "d6a8b0c2e345"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("cambios_devolucion"):
        op.create_table(
            "cambios_devolucion",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("orden_venta_id", sa.Integer(), sa.ForeignKey("orden_venta.id", ondelete="CASCADE"), nullable=False),
            sa.Column("detalle_venta_id", sa.Integer(), sa.ForeignKey("detalle_venta.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tipo", sa.String(20), nullable=False, server_default="cambio"),
            sa.Column("motivo", sa.String(50), nullable=False),
            sa.Column("producto_nuevo_codigo", sa.String(50), sa.ForeignKey("productos.codigo", ondelete="SET NULL"), nullable=True),
            sa.Column("talla_nueva_id", sa.Integer(), sa.ForeignKey("tallas.id", ondelete="SET NULL"), nullable=True),
            sa.Column("color_nuevo_id", sa.Integer(), sa.ForeignKey("colores.id", ondelete="SET NULL"), nullable=True),
            sa.Column("sucursal_id", sa.Integer(), sa.ForeignKey("sucursales.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("fecha_programada", sa.Date(), nullable=False),
            sa.Column("hora_programada", sa.Time(), nullable=True),
            sa.Column("descripcion_problema", sa.Text(), nullable=False),
            sa.Column("estado", sa.String(30), nullable=False, server_default="pendiente"),
            sa.Column("respuesta_encargado", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        for column in ("orden_venta_id", "detalle_venta_id", "sucursal_id"):
            op.create_index(f"ix_cambios_devolucion_{column}", "cambios_devolucion", [column])
    op.add_column("empresas", sa.Column("plazo_cambios_dias", sa.Integer(), nullable=False, server_default="7"))
    op.add_column("cambios_devolucion", sa.Column("nuevo_stock_inventario_id", sa.Integer(), nullable=True))
    op.add_column("cambios_devolucion", sa.Column("precio_original", sa.Numeric(10, 2), nullable=True))
    op.add_column("cambios_devolucion", sa.Column("precio_nuevo", sa.Numeric(10, 2), nullable=True))
    op.add_column("cambios_devolucion", sa.Column("monto_adicional", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("cambios_devolucion", sa.Column("saldo_favor_generado", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("cambios_devolucion", sa.Column("monto_reembolsado", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("cambios_devolucion", sa.Column("metodo_pago_diferencia", sa.String(30), nullable=True))
    op.add_column("cambios_devolucion", sa.Column("nota_venta_numero", sa.String(50), nullable=True))
    op.add_column("cambios_devolucion", sa.Column("orden_ajuste_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_cambio_nuevo_stock", "cambios_devolucion", "stock_inventario", ["nuevo_stock_inventario_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_cambio_orden_ajuste", "cambios_devolucion", "orden_venta", ["orden_ajuste_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_cambio_nota_venta_numero", "cambios_devolucion", ["nota_venta_numero"], unique=True)
    op.create_table(
        "saldos_favor_cliente",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("saldo", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("empresa_id", "user_id", name="uq_saldo_favor_empresa_usuario"),
    )
    op.create_index("ix_saldos_favor_empresa_id", "saldos_favor_cliente", ["empresa_id"])
    op.create_index("ix_saldos_favor_user_id", "saldos_favor_cliente", ["user_id"])
    op.create_table(
        "movimientos_saldo_favor",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("saldo_favor_id", sa.Integer(), sa.ForeignKey("saldos_favor_cliente.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cambio_devolucion_id", sa.Integer(), sa.ForeignKey("cambios_devolucion.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("saldo_resultante", sa.Numeric(10, 2), nullable=False),
        sa.Column("descripcion", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_movimientos_saldo_favor_id", "movimientos_saldo_favor", ["saldo_favor_id"])


def downgrade() -> None:
    op.drop_index("ix_movimientos_saldo_favor_id", table_name="movimientos_saldo_favor")
    op.drop_table("movimientos_saldo_favor")
    op.drop_index("ix_saldos_favor_user_id", table_name="saldos_favor_cliente")
    op.drop_index("ix_saldos_favor_empresa_id", table_name="saldos_favor_cliente")
    op.drop_table("saldos_favor_cliente")
    op.drop_index("ix_cambio_nota_venta_numero", table_name="cambios_devolucion")
    op.drop_constraint("fk_cambio_orden_ajuste", "cambios_devolucion", type_="foreignkey")
    op.drop_constraint("fk_cambio_nuevo_stock", "cambios_devolucion", type_="foreignkey")
    for name in ("orden_ajuste_id", "nota_venta_numero", "metodo_pago_diferencia", "monto_reembolsado", "saldo_favor_generado", "monto_adicional", "precio_nuevo", "precio_original", "nuevo_stock_inventario_id"):
        op.drop_column("cambios_devolucion", name)
    op.drop_column("empresas", "plazo_cambios_dias")
