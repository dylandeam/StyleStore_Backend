"""
Modelo Proveedor (CU16).
Conforme a Especificación StyleStore v5 (Sección 10).
PK: codigo (String(30)).
Con campo CI único y multiasociaciones independientes (Categorias, Temporadas, Colecciones).
"""
from datetime import datetime
from sqlalchemy import String, DateTime, Table, Column, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Tablas intermedias de multiasociación independiente (v5 Sección 10 y 26)
proveedor_categorias = Table(
    "proveedor_categorias",
    Base.metadata,
    Column("proveedor_codigo", String(30), ForeignKey("proveedores.codigo", ondelete="CASCADE"), primary_key=True),
    Column("categoria_id", Integer, ForeignKey("categorias.id", ondelete="CASCADE"), primary_key=True),
)

proveedor_temporadas = Table(
    "proveedor_temporadas",
    Base.metadata,
    Column("proveedor_codigo", String(30), ForeignKey("proveedores.codigo", ondelete="CASCADE"), primary_key=True),
    Column("temporada_id", Integer, ForeignKey("temporadas.id", ondelete="CASCADE"), primary_key=True),
)

proveedor_colecciones = Table(
    "proveedor_colecciones",
    Base.metadata,
    Column("proveedor_codigo", String(30), ForeignKey("proveedores.codigo", ondelete="CASCADE"), primary_key=True),
    Column("coleccion_id", Integer, ForeignKey("colecciones.id", ondelete="CASCADE"), primary_key=True),
)


class Proveedor(Base):
    """Tabla de Proveedores de StyleStore."""

    __tablename__ = "proveedores"

    codigo: Mapped[str] = mapped_column(String(30), primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    ci: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    telefono: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    categorias = relationship("Categoria", secondary=proveedor_categorias, lazy="selectin")
    temporadas = relationship("Temporada", secondary=proveedor_temporadas, lazy="selectin")
    colecciones = relationship("Coleccion", secondary=proveedor_colecciones, lazy="selectin")

    def __repr__(self) -> str:
        return f"<Proveedor(codigo='{self.codigo}', nombre='{self.nombre}', ci='{self.ci}')>"
