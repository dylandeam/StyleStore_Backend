"""
Modelo Orden_Venta y Detalle_Venta (Sección 18).
Conforme a Especificación StyleStore v5.
Fuente de verdad para ventas presenciales y en línea.
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Integer, DateTime, Date, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrdenVenta(Base):
    """Órdenes de venta generadas por compras en línea o en caja presencial."""

    __tablename__ = "orden_venta"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    fecha: Mapped[date] = mapped_column(Date, default=func.current_date(), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="pendiente_pago", nullable=False)  # 'pendiente_pago', 'pagada', 'en_camino', 'entregada', 'cancelada'
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0.00)
    tipo_venta: Mapped[str] = mapped_column(String(30), nullable=False, default="en linea")  # 'presencial' | 'en linea'

    codigo_cliente: Mapped[str] = mapped_column(
        String(30), ForeignKey("clientes.codigo", ondelete="RESTRICT"), nullable=False, index=True
    )
    sucursal_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sucursales.id", ondelete="SET NULL"), nullable=True, index=True
    )
    carrito_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("carritos.id", ondelete="SET NULL"), nullable=True, index=True
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
    carrito = relationship("Carrito", lazy="joined")
    detalles = relationship("DetalleVenta", back_populates="orden_venta", cascade="all, delete-orphan", lazy="selectin")
    pagos = relationship("Pago", back_populates="orden_venta", cascade="all, delete-orphan", lazy="selectin")
    envios = relationship("Envio", back_populates="orden_venta", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<OrdenVenta(id={self.id}, cliente='{self.codigo_cliente}', total={self.total}, tipo='{self.tipo_venta}')>"


class DetalleVenta(Base):
    """Líneas vendidas dentro de una orden de venta."""

    __tablename__ = "detalle_venta"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    orden_venta_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orden_venta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stock_inventario_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("stock_inventario.id", ondelete="SET NULL"), nullable=True, index=True
    )
    producto_nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    color_nombre: Mapped[str | None] = mapped_column(String(50), nullable=True)
    talla_nombre: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relaciones
    orden_venta = relationship("OrdenVenta", back_populates="detalles")
    stock_inventario = relationship("StockInventario", lazy="joined")

    def __repr__(self) -> str:
        return f"<DetalleVenta(id={self.id}, orden={self.orden_venta_id}, cant={self.cantidad}, subtotal={self.subtotal})>"
