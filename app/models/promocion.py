"""Promociones agrupadas y códigos de descuento aislados por tenant."""
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PromocionAgrupada(Base):
    __tablename__ = "promociones_agrupadas"
    __table_args__ = (
        CheckConstraint("porcentaje BETWEEN 1 AND 90", name="ck_promocion_agrupada_porcentaje"),
        CheckConstraint(
            "(tipo = 'categoria' AND categoria_id IS NOT NULL AND temporada_id IS NULL) OR "
            "(tipo = 'temporada' AND temporada_id IS NOT NULL AND categoria_id IS NULL)",
            name="ck_promocion_agrupada_objetivo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    categoria_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categorias.id", ondelete="CASCADE"), nullable=True, index=True)
    temporada_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("temporadas.id", ondelete="CASCADE"), nullable=True, index=True)
    porcentaje: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    categoria = relationship("Categoria", lazy="joined")
    temporada = relationship("Temporada", lazy="joined")


class CodigoDescuento(Base):
    __tablename__ = "codigos_descuento"
    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_codigo_descuento_empresa_codigo"),
        CheckConstraint("porcentaje BETWEEN 1 AND 90", name="ck_codigo_descuento_porcentaje"),
        CheckConstraint("max_usos IS NULL OR max_usos > 0", name="ck_codigo_descuento_max_usos"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    porcentaje: Mapped[int] = mapped_column(Integer, nullable=False)
    aplica_online: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    aplica_presencial: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    fecha_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    max_usos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usos_actual: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
