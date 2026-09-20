"""
Modelo Envio (Sección 20).
Conforme a Especificación StyleStore v5.
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Integer, DateTime, Date, Numeric, Text, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Envio(Base):
    """Tabla de Envíos y despachos a domicilio."""

    __tablename__ = "envios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    orden_venta_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orden_venta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    direccion: Mapped[str] = mapped_column(String(255), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False)
    referencia: Mapped[str | None] = mapped_column(Text, nullable=True)
    costo: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0.00)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="pendiente")  # 'pendiente', 'en camino', 'entregado', 'completado'
    fecha: Mapped[date] = mapped_column(Date, default=func.current_date(), nullable=False)
    yango_tracking_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    yango_tracking_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    delivery_conductor: Mapped[str | None] = mapped_column(String(150), nullable=True)
    ubicacion_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Seguimiento GPS en tiempo real y repartidor (v7 Punto 7)
    token_seguimiento: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    tracking_activo: Mapped[bool | None] = mapped_column(Boolean, default=True, server_default="true", nullable=True)
    repartidor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    repartidor_lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    repartidor_lon: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    repartidor_actualizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    latitud_destino: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    longitud_destino: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    distancia_km: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    minutos_estimados: Mapped[int | None] = mapped_column(Integer, nullable=True)

    @property
    def tracking_code(self) -> str | None:
        return self.yango_tracking_code or self.token_seguimiento

    @tracking_code.setter
    def tracking_code(self, val: str | None) -> None:
        self.yango_tracking_code = val

    @property
    def tracking_url(self) -> str | None:
        return self.yango_tracking_url

    @tracking_url.setter
    def tracking_url(self, val: str | None) -> None:
        self.yango_tracking_url = val

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    orden_venta = relationship("OrdenVenta", back_populates="envios")
    repartidor = relationship("User", foreign_keys=[repartidor_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<Envio(id={self.id}, orden={self.orden_venta_id}, ciudad='{self.ciudad}', estado='{self.estado}')>"
