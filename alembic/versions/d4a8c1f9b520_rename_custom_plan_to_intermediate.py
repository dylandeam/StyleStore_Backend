"""rename custom plan to intermediate

Revision ID: d4a8c1f9b520
Revises: c9f3a2d7e641
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = "d4a8c1f9b520"
down_revision = "c9f3a2d7e641"
branch_labels = None
depends_on = None


plans = sa.table(
    "planes_suscripcion",
    sa.column("id", sa.Integer),
    sa.column("scope_key", sa.String),
    sa.column("codigo", sa.String),
    sa.column("nombre", sa.String),
    sa.column("max_sucursales", sa.Integer),
    sa.column("ia_generativa", sa.Boolean),
    sa.column("capacidades", sa.JSON),
)
contracts = sa.table(
    "contrataciones_plan",
    sa.column("plan_id", sa.Integer),
)

COMMON = {
    "productos": True,
    "ventas": True,
    "reservas": True,
    "offline": True,
    "reportes": True,
}


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        plans.update().where(plans.c.codigo == "basico").values(
            max_sucursales=2,
            ia_generativa=False,
            capacidades={**COMMON, "chatbot": False, "predicciones": False, "ia_generativa": False},
        )
    )
    legacy_rows = connection.execute(
        sa.select(plans.c.id, plans.c.scope_key).where(plans.c.codigo == "personalizado")
    ).all()
    for legacy_id, scope_key in legacy_rows:
        existing_id = connection.execute(
            sa.select(plans.c.id).where(
                plans.c.scope_key == scope_key,
                plans.c.codigo == "intermedio",
            )
        ).scalar_one_or_none()
        if existing_id is not None:
            connection.execute(
                contracts.update().where(contracts.c.plan_id == legacy_id).values(plan_id=existing_id)
            )
            connection.execute(plans.delete().where(plans.c.id == legacy_id))
        else:
            connection.execute(
                plans.update().where(plans.c.id == legacy_id).values(
                    codigo="intermedio",
                    nombre="Intermedio",
                    max_sucursales=5,
                    ia_generativa=False,
                    capacidades={**COMMON, "chatbot": True, "predicciones": False, "ia_generativa": False},
                )
            )
    connection.execute(
        plans.update().where(plans.c.codigo == "profesional").values(
            max_sucursales=sa.case(
                (plans.c.max_sucursales < 10, 10),
                else_=sa.func.coalesce(plans.c.max_sucursales, 10),
            ),
            ia_generativa=True,
            capacidades={**COMMON, "chatbot": True, "predicciones": True, "ia_generativa": True},
        )
    )


def downgrade() -> None:
    op.get_bind().execute(
        plans.update().where(plans.c.codigo == "intermedio").values(
            codigo="personalizado",
            nombre="Personalizado",
        )
    )
