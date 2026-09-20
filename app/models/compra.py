"""
Modelo Compra y DetalleCompra (Punto 2: Módulo de Compras a Proveedores).
Conforme a Especificación StyleStore v7.
Permite el abastecimiento de inventario directamente a una sucursal destino.
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Integer, DateTime, Date, Numeric, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Compra(Base):
    """Compras de mercadería realizadas a proveedores con destino a una sucursal."""

    __tablename__ = "compras"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    fecha: Mapped[date] = mapped_column(Date, default=func.current_date(), nullable=False)
    proveedor_codigo: Mapped[str] = mapped_column(
        String(30), ForeignKey("proveedores.codigo", ondelete="RESTRICT"), nullable=False, index=True
    )
    sucursal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursales.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    nro_factura: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0.00)
    estado: Mapped[str] = mapped_column(String(30), default="registrada", nullable=False)  # 'registrada' | 'anulada'
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    proveedor = relationship("Proveedor", lazy="joined")
    sucursal = relationship("Sucursal", lazy="joined")
    detalles = relationship("DetalleCompra", back_populates="compra", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Compra(id={self.id}, proveedor_codigo='{self.proveedor_codigo}', sucursal_id={self.sucursal_id}, total={self.total})>"


class DetalleCompra(Base):
    """Detalle de artículos abastecidos en una compra."""

    __tablename__ = "detalle_compras"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    compra_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("compras.id", ondelete="CASCADE"), nullable=False, index=True
    )
    producto_codigo: Mapped[str] = mapped_column(
        String(50), ForeignKey("productos.codigo", ondelete="RESTRICT"), nullable=False, index=True
    )
    color_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("colores.id", ondelete="RESTRICT"), nullable=False
    )
    talla_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tallas.id", ondelete="RESTRICT"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relaciones
    compra = relationship("Compra", back_populates="detalles")
    producto = relationship("Producto", lazy="joined")
    color = relationship("Color", lazy="joined")
    talla = relationship("Talla", lazy="joined")

    def __repr__(self) -> str:
        return f"<DetalleCompra(id={self.id}, compra_id={self.compra_id}, producto='{self.producto_codigo}', cant={self.cantidad})>"
