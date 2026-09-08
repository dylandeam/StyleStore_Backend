"""
Modelo Producto (CU10).
Conforme a Especificación StyleStore v4 (Diagrama DB Oficial).
PK: codigo (String(50)).
FK: categoria_id, temporada_id.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, Numeric, Text, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Producto(Base):
    """Product catalog table conforming to official v4 diagram."""

    __tablename__ = "productos"

    codigo: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    foto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    categoria_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categorias.id", ondelete="RESTRICT"), nullable=False
    )
    temporada_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("temporadas.id", ondelete="RESTRICT"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    categoria = relationship("Categoria", backref="productos_rel", lazy="joined")
    temporada = relationship("Temporada", backref="productos_rel", lazy="joined")
    colores_rel = relationship("ProductoColor", back_populates="producto", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Producto(codigo='{self.codigo}', nombre='{self.nombre}', precio={self.precio})>"
