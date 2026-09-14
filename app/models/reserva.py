"""
Modelo Reserva y Detalle_Reserva (CU15 / Sección 16).
Conforme a Especificación StyleStore v5.
"""
from datetime import datetime, date, time
from sqlalchemy import String, Integer, DateTime, Date, Time, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Reserva(Base):
    """Tabla de Reservas de prendas por clientes."""

    __tablename__ = "reservas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    fecha: Mapped[date] = mapped_column(Date, default=func.current_date(), nullable=False)
    hora: Mapped[time] = mapped_column(Time, default=func.current_time(), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="pendiente", nullable=False)  # 'pendiente', 'completada', 'cancelada'

    codigo_cliente: Mapped[str] = mapped_column(
        String(30), ForeignKey("clientes.codigo", ondelete="RESTRICT"), nullable=False, index=True
    )
    sucursal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursales.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    cliente = relationship("Cliente", lazy="joined")
    sucursal = relationship("Sucursal", lazy="joined")
    detalles = relationship("DetalleReserva", back_populates="reserva", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Reserva(id={self.id}, cliente='{self.codigo_cliente}', estado='{self.estado}')>"


class DetalleReserva(Base):
    """Líneas de productos incluidos en una reserva."""

    __tablename__ = "detalle_reserva"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reserva_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reservas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stock_inventario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stock_inventario.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relaciones
    reserva = relationship("Reserva", back_populates="detalles")
    stock_inventario = relationship("StockInventario", lazy="joined")

    def __repr__(self) -> str:
        return f"<DetalleReserva(id={self.id}, reserva_id={self.reserva_id}, cantidad={self.cantidad})>"
