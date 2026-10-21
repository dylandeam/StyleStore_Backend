"""Configurable subscription plans and customer contracts."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PlanSuscripcion(Base):
    __tablename__ = "planes_suscripcion"
    __table_args__ = (
        UniqueConstraint("scope_key", "codigo", name="uq_planes_scope_codigo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int | None] = mapped_column(ForeignKey("empresas.id", ondelete="CASCADE"), index=True)
    scope_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    precio_mensual: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="BOB")
    max_sucursales: Mapped[int | None] = mapped_column(nullable=True)
    ia_generativa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    beneficios: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    capacidades: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    estilo: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    empresa = relationship("Empresa")


class ContratacionPlan(Base):
    __tablename__ = "contrataciones_plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("planes_suscripcion.id", ondelete="RESTRICT"), index=True, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activa")
    estado_pago: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    referencia_pago: Mapped[str | None] = mapped_column(String(120), nullable=True)
    pagado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    precio_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda_snapshot: Mapped[str] = mapped_column(String(3), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    fecha_fin: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plan = relationship("PlanSuscripcion")
    user = relationship("User")
    empresa = relationship("Empresa")
