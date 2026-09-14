"""
Modelo Próximamente (Sección 11).
Conforme a Especificación StyleStore v5.
Prendas y artículos que llegarán en un futuro al inventario.
"""
from datetime import datetime, date
from sqlalchemy import String, Boolean, DateTime, Date, Text, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Proximamente(Base):
    """Prendas que se lanzarán próximamente en StyleStore."""

    __tablename__ = "proximamente"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    foto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fecha_estimada_llegada: Mapped[date | None] = mapped_column(Date, nullable=True)

    proveedor_codigo: Mapped[str | None] = mapped_column(
        String(30), ForeignKey("proveedores.codigo", ondelete="SET NULL"), nullable=True
    )
    categoria_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categorias.id", ondelete="SET NULL"), nullable=True
    )
    temporada_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("temporadas.id", ondelete="SET NULL"), nullable=True
    )
    coleccion_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("colecciones.id", ondelete="SET NULL"), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    proveedor = relationship("Proveedor", lazy="joined")
    categoria = relationship("Categoria", lazy="joined")
    temporada = relationship("Temporada", lazy="joined")
    coleccion = relationship("Coleccion", lazy="joined")

    def __repr__(self) -> str:
        return f"<Proximamente(id={self.id}, nombre='{self.nombre}')>"
