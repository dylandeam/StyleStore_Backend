"""
Modelo Outfit y OutfitItem (Punto 9 / v7).
Permite a los clientes crear, combinar y guardar outfits personalizados
con prendas superiores, inferiores, calzado y accesorios.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, DateTime, Numeric, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Outfit(Base):
    """Combinación de prendas guardada por un cliente."""

    __tablename__ = "outfits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0.00)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    user = relationship("User", lazy="joined")
    items = relationship("OutfitItem", back_populates="outfit", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Outfit(id={self.id}, user_id={self.user_id}, nombre='{self.nombre}', total={self.total})>"


class OutfitItem(Base):
    """Prenda individual que compone un outfit."""

    __tablename__ = "outfit_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    outfit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    producto_codigo: Mapped[str] = mapped_column(
        String(50), ForeignKey("productos.codigo", ondelete="RESTRICT"), nullable=False, index=True
    )
    tipo_prenda: Mapped[str] = mapped_column(String(30), nullable=False, default="superior")  # 'superior', 'inferior', 'calzado', 'accesorio'
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0.00)

    # Relaciones
    outfit = relationship("Outfit", back_populates="items")
    producto = relationship("Producto", lazy="joined")

    def __repr__(self) -> str:
        return f"<OutfitItem(id={self.id}, outfit_id={self.outfit_id}, producto='{self.producto_codigo}', tipo='{self.tipo_prenda}')>"
