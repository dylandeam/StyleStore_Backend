"""
Modelo Pago (Sección 19).
Conforme a Especificación StyleStore v5.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, DateTime, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Pago(Base):
    """Tabla de Pagos de StyleStore (PayPal en línea o caja presencial)."""

    __tablename__ = "pagos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    orden_venta_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orden_venta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tipo_pago: Mapped[str] = mapped_column(String(30), nullable=False, default="en linea")  # 'en linea' | 'en caja'
    metodo_pago: Mapped[str | None] = mapped_column(String(30), nullable=True, default=None)  # 'paypal', 'efectivo', 'qr'
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="pendiente")  # 'pendiente', 'aprobado', 'fallido'
    paypal_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    paypal_capture_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    orden_venta = relationship("OrdenVenta", back_populates="pagos")

    def __repr__(self) -> str:
        return f"<Pago(id={self.id}, orden={self.orden_venta_id}, monto={self.monto}, estado='{self.estado}')>"
