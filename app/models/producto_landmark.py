"""
Modelo ProductoLandmark (Especificación v8).
"""
from datetime import datetime
from typing import Any, Dict
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProductoLandmark(Base):
    """Calibración manual de landmarks clave para RA."""

    __tablename__ = "producto_landmarks"

    producto_codigo: Mapped[str] = mapped_column(
        String(50), ForeignKey("productos.codigo", ondelete="CASCADE"), primary_key=True
    )
    tipo_ar: Mapped[str] = mapped_column(String(30), nullable=False, default="superior")
    landmarks: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    calibrado_por: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    calibrado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ProductoLandmark(producto_codigo='{self.producto_codigo}', tipo_ar='{self.tipo_ar}')>"
