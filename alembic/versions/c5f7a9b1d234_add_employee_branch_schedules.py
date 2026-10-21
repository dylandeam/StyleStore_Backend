"""Add employee workday type and branch schedules.

Revision ID: c5f7a9b1d234
Revises: b4e6f8a0c123
Create Date: 2026-10-21
"""

from alembic import op
import sqlalchemy as sa


revision = "c5f7a9b1d234"
down_revision = "b4e6f8a0c123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empleados",
        sa.Column(
            "jornada_tipo",
            sa.String(length=20),
            nullable=False,
            server_default="tiempo_completo",
        ),
    )
    op.create_check_constraint(
        "ck_empleados_jornada_tipo",
        "empleados",
        "jornada_tipo IN ('tiempo_completo', 'medio_tiempo')",
    )
    op.create_table(
        "empleado_sucursales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "empresa_id",
            sa.Integer(),
            sa.ForeignKey("empresas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "empleado_codigo",
            sa.String(length=30),
            sa.ForeignKey("empleados.codigo", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sucursal_id",
            sa.Integer(),
            sa.ForeignKey("sucursales.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("hora_inicio", sa.Time(), nullable=False),
        sa.Column("hora_fin", sa.Time(), nullable=False),
        sa.Column(
            "dias_semana",
            sa.String(length=80),
            nullable=False,
            server_default="lunes,martes,miercoles,jueves,viernes",
        ),
        sa.CheckConstraint("hora_inicio < hora_fin", name="ck_empleado_sucursal_horas"),
        sa.UniqueConstraint(
            "empleado_codigo", "sucursal_id", name="uq_empleado_sucursal_asignacion"
        ),
    )
    op.create_index(
        "ix_empleado_sucursales_empresa_id", "empleado_sucursales", ["empresa_id"]
    )
    op.create_index(
        "ix_empleado_sucursales_empleado_codigo",
        "empleado_sucursales",
        ["empleado_codigo"],
    )
    op.create_index(
        "ix_empleado_sucursales_sucursal_id",
        "empleado_sucursales",
        ["sucursal_id"],
    )
    op.execute(
        sa.text(
            """
            INSERT INTO empleado_sucursales
                (empresa_id, empleado_codigo, sucursal_id, hora_inicio, hora_fin, dias_semana)
            SELECT COALESCE(s.empresa_id, u.empresa_id), e.codigo, e.sucursal_id,
                   COALESCE(s.hora_apertura, '09:00:00'),
                   COALESCE(s.hora_cierre, '18:00:00'),
                   'lunes,martes,miercoles,jueves,viernes'
            FROM empleados e
            JOIN users u ON u.id = e.user_id
            JOIN sucursales s ON s.id = e.sucursal_id
            WHERE COALESCE(s.empresa_id, u.empresa_id) IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_empleado_sucursales_sucursal_id", table_name="empleado_sucursales")
    op.drop_index(
        "ix_empleado_sucursales_empleado_codigo", table_name="empleado_sucursales"
    )
    op.drop_index("ix_empleado_sucursales_empresa_id", table_name="empleado_sucursales")
    op.drop_table("empleado_sucursales")
    op.drop_constraint("ck_empleados_jornada_tipo", "empleados", type_="check")
    op.drop_column("empleados", "jornada_tipo")
