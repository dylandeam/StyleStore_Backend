"""
Modelo Colección (CU15).
Conforme a Especificación StyleStore v5.
"""
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Coleccion(Base):
    """Tabla de Colecciones de prendas de StyleStore."""

    __tablename__ = "colecciones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    productos = relationship("Producto", back_populates="coleccion", lazy="select")

    @property
    def productos_count(self) -> int:
        return len(self.productos) if self.productos else 0

    def __repr__(self) -> str:
        return f"<Coleccion(id={self.id}, nombre='{self.nombre}')>"
