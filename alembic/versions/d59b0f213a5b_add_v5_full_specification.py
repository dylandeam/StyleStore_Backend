"""add v5 full specification tables and columns

Revision ID: d59b0f213a5b
Revises: c48a9e102f4a
Create Date: 2026-09-14 03:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd59b0f213a5b'
down_revision: Union[str, Sequence[str], None] = 'c48a9e102f4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)
    op.create_index(op.f('ix_roles_nombre'), 'roles', ['nombre'], unique=True)

    # 2. Add role_id and profile fields to users
    op.add_column('users', sa.Column('telefono', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('direccion', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('foto', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('role_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_users_role_id_roles', 'users', 'roles', ['role_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_users_role_id'), 'users', ['role_id'], unique=False)

    # 3. Add role_id to role_permissions
    op.add_column('role_permissions', sa.Column('role_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_role_permissions_role_id_roles', 'role_permissions', 'roles', ['role_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_role_permissions_role_id'), 'role_permissions', ['role_id'], unique=False)

    # 4. Colecciones table
    op.create_table(
        'colecciones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_colecciones_id'), 'colecciones', ['id'], unique=False)
    op.create_index(op.f('ix_colecciones_nombre'), 'colecciones', ['nombre'], unique=True)

    # 5. Add coleccion_id and visible_en_catalogo to productos
    op.add_column('productos', sa.Column('coleccion_id', sa.Integer(), nullable=True))
    op.add_column('productos', sa.Column('visible_en_catalogo', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.create_foreign_key('fk_productos_coleccion_id_colecciones', 'productos', 'colecciones', ['coleccion_id'], ['id'], ondelete='RESTRICT')

    # 6. Add ci to proveedores and multi-association tables
    op.add_column('proveedores', sa.Column('ci', sa.String(length=20), nullable=True))
    op.create_index(op.f('ix_proveedores_ci'), 'proveedores', ['ci'], unique=True)

    op.create_table(
        'proveedor_categorias',
        sa.Column('proveedor_codigo', sa.String(length=30), nullable=False),
        sa.Column('categoria_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['proveedor_codigo'], ['proveedores.codigo'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('proveedor_codigo', 'categoria_id')
    )

    op.create_table(
        'proveedor_temporadas',
        sa.Column('proveedor_codigo', sa.String(length=30), nullable=False),
        sa.Column('temporada_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['proveedor_codigo'], ['proveedores.codigo'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['temporada_id'], ['temporadas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('proveedor_codigo', 'temporada_id')
    )

    op.create_table(
        'proveedor_colecciones',
        sa.Column('proveedor_codigo', sa.String(length=30), nullable=False),
        sa.Column('coleccion_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['coleccion_id'], ['colecciones.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['proveedor_codigo'], ['proveedores.codigo'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('proveedor_codigo', 'coleccion_id')
    )

    # 7. Proximamente table
    op.create_table(
        'proximamente',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=150), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('foto', sa.String(length=255), nullable=True),
        sa.Column('fecha_estimada_llegada', sa.Date(), nullable=True),
        sa.Column('proveedor_codigo', sa.String(length=30), nullable=True),
        sa.Column('categoria_id', sa.Integer(), nullable=True),
        sa.Column('temporada_id', sa.Integer(), nullable=True),
        sa.Column('coleccion_id', sa.Integer(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['coleccion_id'], ['colecciones.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['proveedor_codigo'], ['proveedores.codigo'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['temporada_id'], ['temporadas.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_proximamente_id'), 'proximamente', ['id'], unique=False)
    op.create_index(op.f('ix_proximamente_nombre'), 'proximamente', ['nombre'], unique=False)

    # 8. Reservas and DetalleReserva
    op.create_table(
        'reservas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('hora', sa.Time(), nullable=False),
        sa.Column('estado', sa.String(length=30), nullable=False, server_default='pendiente'),
        sa.Column('codigo_cliente', sa.String(length=30), nullable=False),
        sa.Column('sucursal_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['codigo_cliente'], ['clientes.codigo'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['sucursal_id'], ['sucursales.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reservas_id'), 'reservas', ['id'], unique=False)
    op.create_index(op.f('ix_reservas_codigo_cliente'), 'reservas', ['codigo_cliente'], unique=False)
    op.create_index(op.f('ix_reservas_sucursal_id'), 'reservas', ['sucursal_id'], unique=False)

    op.create_table(
        'detalle_reserva',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reserva_id', sa.Integer(), nullable=False),
        sa.Column('stock_inventario_id', sa.Integer(), nullable=False),
        sa.Column('cantidad', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['reserva_id'], ['reservas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stock_inventario_id'], ['stock_inventario.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_detalle_reserva_id'), 'detalle_reserva', ['id'], unique=False)
    op.create_index(op.f('ix_detalle_reserva_reserva_id'), 'detalle_reserva', ['reserva_id'], unique=False)

    # 9. Carritos and DetalleCarrito
    op.create_table(
        'carritos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('estado', sa.String(length=30), nullable=False, server_default='activo'),
        sa.Column('codigo_cliente', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['codigo_cliente'], ['clientes.codigo'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_carritos_id'), 'carritos', ['id'], unique=False)
    op.create_index(op.f('ix_carritos_codigo_cliente'), 'carritos', ['codigo_cliente'], unique=False)

    op.create_table(
        'detalle_carrito',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('carrito_id', sa.Integer(), nullable=False),
        sa.Column('stock_inventario_id', sa.Integer(), nullable=False),
        sa.Column('cantidad', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('precio_unitario', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['carrito_id'], ['carritos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stock_inventario_id'], ['stock_inventario.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_detalle_carrito_id'), 'detalle_carrito', ['id'], unique=False)
    op.create_index(op.f('ix_detalle_carrito_carrito_id'), 'detalle_carrito', ['carrito_id'], unique=False)

    # 10. OrdenVenta and DetalleVenta
    op.create_table(
        'orden_venta',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('estado', sa.String(length=30), nullable=False, server_default='pendiente_pago'),
        sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('tipo_venta', sa.String(length=30), nullable=False, server_default='en linea'),
        sa.Column('codigo_cliente', sa.String(length=30), nullable=False),
        sa.Column('sucursal_id', sa.Integer(), nullable=True),
        sa.Column('carrito_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['carrito_id'], ['carritos.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['codigo_cliente'], ['clientes.codigo'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['sucursal_id'], ['sucursales.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orden_venta_id'), 'orden_venta', ['id'], unique=False)
    op.create_index(op.f('ix_orden_venta_codigo_cliente'), 'orden_venta', ['codigo_cliente'], unique=False)

    op.create_table(
        'detalle_venta',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('orden_venta_id', sa.Integer(), nullable=False),
        sa.Column('stock_inventario_id', sa.Integer(), nullable=True),
        sa.Column('producto_nombre', sa.String(length=150), nullable=False),
        sa.Column('color_nombre', sa.String(length=50), nullable=True),
        sa.Column('talla_nombre', sa.String(length=20), nullable=True),
        sa.Column('cantidad', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('precio_unitario', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['orden_venta_id'], ['orden_venta.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stock_inventario_id'], ['stock_inventario.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_detalle_venta_id'), 'detalle_venta', ['id'], unique=False)
    op.create_index(op.f('ix_detalle_venta_orden_venta_id'), 'detalle_venta', ['orden_venta_id'], unique=False)

    # 11. Pagos table
    op.create_table(
        'pagos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('orden_venta_id', sa.Integer(), nullable=False),
        sa.Column('monto', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('tipo_pago', sa.String(length=30), nullable=False, server_default='en linea'),
        sa.Column('estado', sa.String(length=30), nullable=False, server_default='pendiente'),
        sa.Column('paypal_order_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['orden_venta_id'], ['orden_venta.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pagos_id'), 'pagos', ['id'], unique=False)
    op.create_index(op.f('ix_pagos_orden_venta_id'), 'pagos', ['orden_venta_id'], unique=False)

    # 12. Envios table
    op.create_table(
        'envios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('orden_venta_id', sa.Integer(), nullable=False),
        sa.Column('direccion', sa.String(length=255), nullable=False),
        sa.Column('ciudad', sa.String(length=100), nullable=False),
        sa.Column('referencia', sa.Text(), nullable=True),
        sa.Column('costo', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('estado', sa.String(length=30), nullable=False, server_default='pendiente'),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['orden_venta_id'], ['orden_venta.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_envios_id'), 'envios', ['id'], unique=False)
    op.create_index(op.f('ix_envios_orden_venta_id'), 'envios', ['orden_venta_id'], unique=False)


def downgrade() -> None:
    op.drop_table('envios')
    op.drop_table('pagos')
    op.drop_table('detalle_venta')
    op.drop_table('orden_venta')
    op.drop_table('detalle_carrito')
    op.drop_table('carritos')
    op.drop_table('detalle_reserva')
    op.drop_table('reservas')
    op.drop_table('proximamente')
    op.drop_table('proveedor_colecciones')
    op.drop_table('proveedor_temporadas')
    op.drop_table('proveedor_categorias')
    op.drop_index(op.f('ix_proveedores_ci'), table_name='proveedores')
    op.drop_column('proveedores', 'ci')
    op.drop_constraint('fk_productos_coleccion_id_colecciones', 'productos', type_='foreignkey')
    op.drop_column('productos', 'visible_en_catalogo')
    op.drop_column('productos', 'coleccion_id')
    op.drop_table('colecciones')
    op.drop_constraint('fk_role_permissions_role_id_roles', 'role_permissions', type_='foreignkey')
    op.drop_column('role_permissions', 'role_id')
    op.drop_constraint('fk_users_role_id_roles', 'users', type_='foreignkey')
    op.drop_column('users', 'role_id')
    op.drop_column('users', 'foto')
    op.drop_column('users', 'direccion')
    op.drop_column('users', 'telefono')
    op.drop_table('roles')
