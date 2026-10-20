"""
Modelo Categoria (CU11).
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Categoria(Base):
    """Tabla de Categorías de prendas."""

    __tablename__ = "categorias"
    __table_args__ = (UniqueConstraint("empresa_id", "nombre", name="uq_categorias_empresa_nombre"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    empresa_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    tipo_ar: Mapped[str | None] = mapped_column(String(30), default="superior", nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Categoria(id={self.id}, nombre='{self.nombre}')>"
