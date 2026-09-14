"""
Modelo Envio (Sección 20).
Conforme a Especificación StyleStore v5.
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Integer, DateTime, Date, Numeric, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Envio(Base):
    """Tabla de Envíos y despachos a domicilio."""

    __tablename__ = "envios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    orden_venta_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orden_venta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    direccion: Mapped[str] = mapped_column(String(255), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False)
    referencia: Mapped[str | None] = mapped_column(Text, nullable=True)
    costo: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0.00)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="pendiente")  # 'pendiente', 'completado'
    fecha: Mapped[date] = mapped_column(Date, default=func.current_date(), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    orden_venta = relationship("OrdenVenta", back_populates="envios")

    def __repr__(self) -> str:
        return f"<Envio(id={self.id}, orden={self.orden_venta_id}, ciudad='{self.ciudad}', estado='{self.estado}')>"
