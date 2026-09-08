"""
Modelo Stock_Inventario.
Conforme a Especificación StyleStore v4 (Diagrama DB Oficial).
# TODO-CONFIRMAR con el equipo: El diagrama oficial no incluye 'cantidad/stock',
se agrega aquí 'cantidad: int' por sentido común funcional para que opere el inventario.
"""
from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StockInventario(Base):
    """Tabla de inventario de existencias por producto, color, talla y sucursal."""

    __tablename__ = "stock_inventario"
    __table_args__ = (
        UniqueConstraint(
            "producto_color_id", "talla_id", "sucursal_id", name="uq_stock_prod_talla_sucursal"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    producto_color_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("producto_colores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    talla_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tallas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sucursal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursales.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # TODO-CONFIRMAR: Campo de cantidad agregado para resolver el vacío del diagrama
    cantidad: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    producto_color = relationship("ProductoColor", back_populates="inventarios_rel")
    talla = relationship("Talla", backref="inventarios_rel", lazy="joined")
    sucursal = relationship("Sucursal", backref="inventarios_rel", lazy="joined")

    def __repr__(self) -> str:
        return f"<StockInventario(id={self.id}, producto_color_id={self.producto_color_id}, talla_id={self.talla_id}, sucursal_id={self.sucursal_id}, cantidad={self.cantidad})>"
