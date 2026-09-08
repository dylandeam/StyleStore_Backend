"""
Modelo ProductoColor (Producto - Color N-a-N).
Conforme a Especificación StyleStore v4.
"""
from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductoColor(Base):
    """Asociación entre Producto y Color."""

    __tablename__ = "producto_colores"
    __table_args__ = (
        UniqueConstraint("producto_codigo", "color_id", name="uq_producto_color"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    producto_codigo: Mapped[str] = mapped_column(
        String(50), ForeignKey("productos.codigo", ondelete="CASCADE"), nullable=False, index=True
    )
    color_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("colores.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Relaciones
    producto = relationship("Producto", back_populates="colores_rel")
    color = relationship("Color", backref="producto_colores_rel", lazy="joined")
    inventarios_rel = relationship("StockInventario", back_populates="producto_color", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ProductoColor(id={self.id}, producto_codigo='{self.producto_codigo}', color_id={self.color_id})>"
