"""Reseñas públicas vinculadas a una prenda y aisladas por tenant."""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ResenaProducto(Base):
    __tablename__ = "resenas_producto"
    __table_args__ = (
        CheckConstraint("puntuacion >= 1 AND puntuacion <= 5", name="ck_resena_producto_puntuacion"),
        UniqueConstraint("empresa_id", "producto_codigo", "user_id", name="uq_resena_producto_usuario"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    producto_codigo: Mapped[str] = mapped_column(
        String(50), ForeignKey("productos.codigo", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    puntuacion: Mapped[int] = mapped_column(Integer, nullable=False)
    comentario: Mapped[str] = mapped_column(Text, nullable=False)
    client_operation_uuid: Mapped[str | None] = mapped_column(
        String(36), nullable=True, unique=True, index=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", lazy="joined")
    producto = relationship("Producto", lazy="joined")

