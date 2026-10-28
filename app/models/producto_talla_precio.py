"""Precio general de una talla para un producto."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductoTallaPrecio(Base):
    __tablename__ = "producto_talla_precios"
    __table_args__ = (
        UniqueConstraint("producto_codigo", "talla_id", name="uq_producto_talla_precio"),
        CheckConstraint("precio > 0", name="ck_producto_talla_precio_positivo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    producto_codigo: Mapped[str] = mapped_column(
        String(50), ForeignKey("productos.codigo", ondelete="CASCADE"), nullable=False, index=True
    )
    talla_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tallas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    precio: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    producto = relationship("Producto", back_populates="precios_talla_rel")
    talla = relationship("Talla", lazy="joined")
