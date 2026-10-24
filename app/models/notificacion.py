"""
Modelos de Notificaciones y Suscripciones (v6 Punto 5).
Conforme a Especificación StyleStore v6.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func, Text, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Notificacion(Base):
    """Tabla de notificaciones para usuarios (clientes y empleados)."""

    __tablename__ = "notificaciones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pago_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pagos.id", ondelete="SET NULL"), nullable=True, unique=True, index=True
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


class PushDevice(Base):
    """FCM installation registered for one user in one tenant context."""

    __tablename__ = "push_devices"
    __table_args__ = (
        UniqueConstraint("token", name="uq_push_devices_token"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(512), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False, default="android")
    device_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CampanaNotificacion(Base):
    """Campaña persistente, inmediata o programada, con alcance multitenant."""

    __tablename__ = "campanas_notificacion"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    empresa_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    url_accion: Mapped[str | None] = mapped_column(String(300), nullable=True)
    audiencia: Mapped[str] = mapped_column(String(40), nullable=False)
    target_user_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    target_empresa_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    enviar_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurrencia_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    proxima_ejecucion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="programada", index=True)
    total_destinatarios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_enviados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ultima_ejecucion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EntregaCampanaNotificacion(Base):
    """Marca idempotente de una entrega de campaña a usuario/tenant/ocurrencia."""

    __tablename__ = "entregas_campana_notificacion"
    __table_args__ = (
        UniqueConstraint(
            "campana_id", "user_id", "empresa_id", "ejecucion_programada",
            name="uq_entrega_campana_destinatario_ejecucion",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campana_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campanas_notificacion.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ejecucion_programada: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
