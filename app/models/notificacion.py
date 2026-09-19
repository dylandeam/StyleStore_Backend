"""
Modelos de Notificaciones y Suscripciones (v6 Punto 5).
Conforme a Especificación StyleStore v6.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Notificacion(Base):
    """Tabla de notificaciones para usuarios (clientes y empleados)."""

    __tablename__ = "notificaciones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(
        String(50), nullable=False, default="general"
    )  # 'recordatorio_reserva', 'proximamente', 'stock_disponible', 'cambio_devolucion', 'general'
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    leida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    url_accion: Mapped[str | None] = mapped_column(String(300), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relaciones
    user = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return f"<Notificacion(id={self.id}, user_id={self.user_id}, tipo='{self.tipo}', leida={self.leida})>"


class SuscripcionProximamente(Base):
    """Suscripción de clientes para ser notificados cuando un artículo de Próximamente esté disponible."""

    __tablename__ = "suscripciones_proximamente"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    proximamente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("proximamente.id", ondelete="CASCADE"), nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User", lazy="joined")
    proximamente = relationship("Proximamente", lazy="joined")


class SuscripcionStock(Base):
    """Suscripción de clientes para avisar cuando se reponga stock de una prenda."""

    __tablename__ = "suscripciones_stock"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stock_inventario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stock_inventario.id", ondelete="CASCADE"), nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User", lazy="joined")
    stock_inventario = relationship("StockInventario", lazy="joined")
