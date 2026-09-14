"""
Modelo Carrito y Detalle_Carrito (Sección 17).
Conforme a Especificación StyleStore v5.
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Integer, DateTime, Date, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Carrito(Base):
    """Carrito de compras de clientes."""

    __tablename__ = "carritos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    fecha: Mapped[date] = mapped_column(Date, default=func.current_date(), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="activo", nullable=False)  # 'activo', 'confirmado', 'abandonado'

    codigo_cliente: Mapped[str] = mapped_column(
        String(30), ForeignKey("clientes.codigo", ondelete="RESTRICT"), nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    cliente = relationship("Cliente", lazy="joined")
    items = relationship("DetalleCarrito", back_populates="carrito", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Carrito(id={self.id}, cliente='{self.codigo_cliente}', estado='{self.estado}')>"


class DetalleCarrito(Base):
    """Ítems dentro del carrito de compras."""

    __tablename__ = "detalle_carrito"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    carrito_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("carritos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stock_inventario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stock_inventario.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relaciones
    carrito = relationship("Carrito", back_populates="items")
    stock_inventario = relationship("StockInventario", lazy="joined")

    def __repr__(self) -> str:
        return f"<DetalleCarrito(id={self.id}, carrito_id={self.carrito_id}, cantidad={self.cantidad}, precio={self.precio_unitario})>"
