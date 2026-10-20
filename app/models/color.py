"""
Modelo Color (CU12).
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Color(Base):
    """Tabla de Colores de prendas."""

    __tablename__ = "colores"
    __table_args__ = (UniqueConstraint("empresa_id", "nombre", name="uq_colores_empresa_nombre"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    empresa_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=True, index=True)
    nombre: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Color(id={self.id}, nombre='{self.nombre}')>"
