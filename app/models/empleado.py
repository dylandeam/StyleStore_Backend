"""
Modelo Empleado (CU8).
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Empleado(Base):
    """Tabla de Empleados del sistema."""

    __tablename__ = "empleados"

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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", backref="empleado_rel", lazy="joined")
    sucursal = relationship("Sucursal", backref="empleados_rel", lazy="joined")

    def __repr__(self) -> str:
        return f"<Empleado(codigo='{self.codigo}', user_id={self.user_id}, sucursal_id={self.sucursal_id})>"
