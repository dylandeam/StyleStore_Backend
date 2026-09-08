"""add v4 diagram entities and relations

Revision ID: c48a9e102f4a
Revises: b37b8d0e518c
Create Date: 2026-09-08 03:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c48a9e102f4a'
down_revision: Union[str, Sequence[str], None] = 'b37b8d0e518c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add apellido and ci to users
    op.add_column('users', sa.Column('apellido', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('ci', sa.String(length=20), nullable=True))
    op.create_index(op.f('ix_users_ci'), 'users', ['ci'], unique=False)

    # 2. Empleados table
    op.create_table(
        'empleados',
        sa.Column('codigo', sa.String(length=30), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('sucursal_id', sa.Integer(), nullable=False),
        sa.Column('edad', sa.Integer(), nullable=False),
        sa.Column('sueldo', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('telefono', sa.String(length=20), nullable=False),
        sa.Column('direccion', sa.String(length=255), nullable=False),
        sa.Column('foto', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['sucursal_id'], ['sucursales.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('codigo'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_empleados_codigo'), 'empleados', ['codigo'], unique=False)

    # 3. Clientes table (sin foto según diagrama v4)
    op.create_table(
        'clientes',
        sa.Column('codigo', sa.String(length=30), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('telefono', sa.String(length=20), nullable=False),
        sa.Column('direccion', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('codigo'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_clientes_codigo'), 'clientes', ['codigo'], unique=False)

    # 4. Catalog Master Tables
    op.create_table(
        'categorias',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_categorias_id'), 'categorias', ['id'], unique=False)
    op.create_index(op.f('ix_categorias_nombre'), 'categorias', ['nombre'], unique=True)

    op.create_table(
        'colores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_colores_id'), 'colores', ['id'], unique=False)
    op.create_index(op.f('ix_colores_nombre'), 'colores', ['nombre'], unique=True)

    op.create_table(
        'tallas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tallas_id'), 'tallas', ['id'], unique=False)
    op.create_index(op.f('ix_tallas_nombre'), 'tallas', ['nombre'], unique=True)

    op.create_table(
        'temporadas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_temporadas_id'), 'temporadas', ['id'], unique=False)
    op.create_index(op.f('ix_temporadas_nombre'), 'temporadas', ['nombre'], unique=True)

    # 5. Recrear productos con el esquema oficial del diagrama v4
    op.drop_table('productos')
    op.create_table(
        'productos',
        sa.Column('codigo', sa.String(length=50), nullable=False),
        sa.Column('nombre', sa.String(length=150), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('foto', sa.String(length=255), nullable=True),
        sa.Column('precio', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('categoria_id', sa.Integer(), nullable=False),
        sa.Column('temporada_id', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['temporada_id'], ['temporadas.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('codigo')
    )
    op.create_index(op.f('ix_productos_codigo'), 'productos', ['codigo'], unique=False)
    op.create_index(op.f('ix_productos_nombre'), 'productos', ['nombre'], unique=False)

    # 6. Producto_Colores table
    op.create_table(
        'producto_colores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('producto_codigo', sa.String(length=50), nullable=False),
        sa.Column('color_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['color_id'], ['colores.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['producto_codigo'], ['productos.codigo'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('producto_codigo', 'color_id', name='uq_producto_color')
    )
    op.create_index(op.f('ix_producto_colores_color_id'), 'producto_colores', ['color_id'], unique=False)
    op.create_index(op.f('ix_producto_colores_id'), 'producto_colores', ['id'], unique=False)
    op.create_index(op.f('ix_producto_colores_producto_codigo'), 'producto_colores', ['producto_codigo'], unique=False)

    # 7. Stock_Inventario table
    op.create_table(
        'stock_inventario',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('producto_color_id', sa.Integer(), nullable=False),
        sa.Column('talla_id', sa.Integer(), nullable=False),
        sa.Column('sucursal_id', sa.Integer(), nullable=False),
        sa.Column('cantidad', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['producto_color_id'], ['producto_colores.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sucursal_id'], ['sucursales.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['talla_id'], ['tallas.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('producto_color_id', 'talla_id', 'sucursal_id', name='uq_stock_prod_talla_sucursal')
    )
    op.create_index(op.f('ix_stock_inventario_id'), 'stock_inventario', ['id'], unique=False)
    op.create_index(op.f('ix_stock_inventario_producto_color_id'), 'stock_inventario', ['producto_color_id'], unique=False)
    op.create_index(op.f('ix_stock_inventario_sucursal_id'), 'stock_inventario', ['sucursal_id'], unique=False)
    op.create_index(op.f('ix_stock_inventario_talla_id'), 'stock_inventario', ['talla_id'], unique=False)

    # 8. Proveedores table (sin CI según diagrama v4)
    op.create_table(
        'proveedores',
        sa.Column('codigo', sa.String(length=30), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('apellido', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('telefono', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('codigo'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_proveedores_codigo'), 'proveedores', ['codigo'], unique=False)


def downgrade() -> None:
    op.drop_table('proveedores')
    op.drop_table('stock_inventario')
    op.drop_table('producto_colores')
    op.drop_table('productos')
    op.drop_table('temporadas')
    op.drop_table('tallas')
    op.drop_table('colores')
    op.drop_table('categorias')
    op.drop_table('clientes')
    op.drop_table('empleados')
    op.drop_index(op.f('ix_users_ci'), table_name='users')
    op.drop_column('users', 'ci')
    op.drop_column('users', 'apellido')
