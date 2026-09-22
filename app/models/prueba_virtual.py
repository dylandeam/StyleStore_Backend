"""
Modelo PruebaVirtual (Especificación v8).
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PruebaVirtual(Base):
    """Historial y trabajos de prueba virtual por foto."""

    __tablename__ = "pruebas_virtuales"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    producto_codigo: Mapped[str] = mapped_column(
        String(50), ForeignKey("productos.codigo", ondelete="CASCADE"), nullable=False
    )
    foto_persona_url: Mapped[str] = mapped_column(String(500), nullable=False)
    foto_resultado_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="procesando", nullable=False)
    mensaje_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<PruebaVirtual(id={self.id}, user_id={self.user_id}, estado='{self.estado}')>"
