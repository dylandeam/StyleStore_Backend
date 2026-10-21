"""
Modelo Empleado (CU8).
"""
from datetime import datetime
from decimal import Decimal
from datetime import time
from sqlalchemy import CheckConstraint, String, Integer, Numeric, DateTime, ForeignKey, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Empleado(Base):
    """Tabla de Empleados del sistema."""

    __tablename__ = "empleados"
    __table_args__ = (
        CheckConstraint(
            "jornada_tipo IN ('tiempo_completo', 'medio_tiempo')",
            name="ck_empleados_jornada_tipo",
        ),
    )

    codigo: Mapped[str] = mapped_column(String(30), primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    sucursal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursales.id", ondelete="RESTRICT"), nullable=False
    )
    edad: Mapped[int] = mapped_column(Integer, nullable=False)
    sueldo: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    telefono: Mapped[str] = mapped_column(String(20), nullable=False)
    direccion: Mapped[str] = mapped_column(String(255), nullable=False)
    foto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jornada_tipo: Mapped[str] = mapped_column(
        String(20), nullable=False, default="tiempo_completo", server_default="tiempo_completo"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", backref="empleado_rel", lazy="joined")
    sucursal = relationship("Sucursal", backref="empleados_rel", lazy="joined")
    asignaciones = relationship(
        "EmpleadoSucursal",
        back_populates="empleado",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="EmpleadoSucursal.id",
    )

    def __repr__(self) -> str:
        return f"<Empleado(codigo='{self.codigo}', user_id={self.user_id}, sucursal_id={self.sucursal_id})>"


class EmpleadoSucursal(Base):
    """Asignación horaria de un empleado a una sucursal de su tenant."""

    __tablename__ = "empleado_sucursales"
    __table_args__ = (
        CheckConstraint("hora_inicio < hora_fin", name="ck_empleado_sucursal_horas"),
        UniqueConstraint(
            "empleado_codigo", "sucursal_id", name="uq_empleado_sucursal_asignacion"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    empleado_codigo: Mapped[str] = mapped_column(
        String(30), ForeignKey("empleados.codigo", ondelete="CASCADE"), nullable=False, index=True
    )
    sucursal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursales.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    dias_semana: Mapped[str] = mapped_column(
        String(80), nullable=False, default="lunes,martes,miercoles,jueves,viernes"
    )

    empleado = relationship("Empleado", back_populates="asignaciones")
    sucursal = relationship("Sucursal", lazy="joined")
