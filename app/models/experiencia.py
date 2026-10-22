"""Calificaciones de servicio y reclamos poscompra por tenant."""
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CalificacionServicio(Base):
    __tablename__ = "calificaciones_servicio"
    __table_args__ = (
        UniqueConstraint("user_id", "orden_venta_id", name="uq_calificacion_usuario_orden"),
        CheckConstraint("puntuacion >= 1 AND puntuacion <= 5", name="ck_calificacion_puntuacion_1_5"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    orden_venta_id: Mapped[int] = mapped_column(Integer, ForeignKey("orden_venta.id", ondelete="CASCADE"), index=True)
    sucursal_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sucursales.id", ondelete="SET NULL"), nullable=True, index=True)
    puntuacion: Mapped[int] = mapped_column(Integer, nullable=False)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    empresa = relationship("Empresa")
    user = relationship("User")
    orden = relationship("OrdenVenta")
    sucursal = relationship("Sucursal")


class Reclamo(Base):
    __tablename__ = "reclamos"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    orden_venta_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("orden_venta.id", ondelete="SET NULL"), nullable=True, index=True)
    calificacion_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("calificaciones_servicio.id", ondelete="SET NULL"), nullable=True, index=True)
    sucursal_id: Mapped[int] = mapped_column(Integer, ForeignKey("sucursales.id", ondelete="RESTRICT"), index=True)
    fecha_incidente: Mapped[date] = mapped_column(Date, nullable=False)
    motivo: Mapped[str] = mapped_column(String(40), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="recibido", server_default="recibido", index=True)
    respuesta: Mapped[str | None] = mapped_column(Text, nullable=True)
    resuelto_por_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resuelto_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    empresa = relationship("Empresa")
    user = relationship("User", foreign_keys=[user_id])
    resuelto_por = relationship("User", foreign_keys=[resuelto_por_id])
    orden = relationship("OrdenVenta")
    calificacion = relationship("CalificacionServicio")
    sucursal = relationship("Sucursal")
