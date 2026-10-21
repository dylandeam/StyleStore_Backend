"""Transferencias de existencias entre sucursales del mismo tenant."""
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TraspasoInventario(Base):
    __tablename__ = "traspasos_inventario"
    __table_args__ = (
        UniqueConstraint("empresa_id", "idempotency_key", name="uq_traspaso_empresa_idempotency"),
        CheckConstraint("cantidad > 0", name="ck_traspaso_cantidad_positiva"),
        CheckConstraint("sucursal_origen_id <> sucursal_destino_id", name="ck_traspaso_sucursales_distintas"),
        CheckConstraint(
            "estado IN ('pendiente', 'aprobado', 'rechazado', 'cancelado')",
            name="ck_traspaso_estado",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sucursal_origen_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursales.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sucursal_destino_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursales.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    producto_color_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("producto_colores.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    talla_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tallas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente", server_default="pendiente", index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    observacion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    respuesta: Mapped[str | None] = mapped_column(String(500), nullable=True)
    solicitado_por_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    procesado_por_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    procesado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sucursal_origen = relationship("Sucursal", foreign_keys=[sucursal_origen_id], lazy="joined")
    sucursal_destino = relationship("Sucursal", foreign_keys=[sucursal_destino_id], lazy="joined")
    producto_color = relationship("ProductoColor", lazy="joined")
    talla = relationship("Talla", lazy="joined")
    solicitado_por = relationship("User", foreign_keys=[solicitado_por_id], lazy="joined")
    procesado_por = relationship("User", foreign_keys=[procesado_por_id], lazy="joined")

