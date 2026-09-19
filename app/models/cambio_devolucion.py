"""
Modelo CambioDevolucion (v6 Punto 9).
Conforme a Especificación StyleStore v6.
"""
from datetime import datetime, date, time
from sqlalchemy import String, Integer, Date, Time, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CambioDevolucion(Base):
    """Tabla de solicitudes y registros de cambio o devolución de prendas por clientes."""

    __tablename__ = "cambios_devolucion"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    orden_venta_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orden_venta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    detalle_venta_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("detalle_venta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(
        String(20), nullable=False, default="cambio"
    )  # 'cambio' | 'devolucion'
    motivo: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'talla_incorrecta', 'color_incorrecto', 'producto_danado', 'disconformidad', 'otro'

    producto_nuevo_codigo: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("productos.codigo", ondelete="SET NULL"), nullable=True
    )
    talla_nueva_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tallas.id", ondelete="SET NULL"), nullable=True
    )
    color_nuevo_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("colores.id", ondelete="SET NULL"), nullable=True
    )

    sucursal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursales.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    fecha_programada: Mapped[date] = mapped_column(Date, nullable=False)
    hora_programada: Mapped[time | None] = mapped_column(Time, nullable=True)

    descripcion_problema: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pendiente"
    )  # 'pendiente', 'aceptada', 'rechazada', 'completada'
    respuesta_encargado: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    orden_venta = relationship("OrdenVenta", lazy="joined")
    detalle_venta = relationship("DetalleVenta", lazy="joined")
    sucursal = relationship("Sucursal", lazy="joined")
    talla_nueva = relationship("Talla", lazy="joined", foreign_keys=[talla_nueva_id])
    color_nuevo = relationship("Color", lazy="joined", foreign_keys=[color_nuevo_id])
    producto_nuevo = relationship("Producto", lazy="joined", foreign_keys=[producto_nuevo_codigo])

    def __repr__(self) -> str:
        return f"<CambioDevolucion(id={self.id}, orden={self.orden_venta_id}, tipo='{self.tipo}', estado='{self.estado}')>"
