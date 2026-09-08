"""
Modelo Proveedor (CU16).
Conforme a Especificación StyleStore v4 (Diagrama DB Oficial).
Sin campo CI según diagrama. PK: codigo.
"""
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Proveedor(Base):
    """Tabla de Proveedores de StyleStore."""

    __tablename__ = "proveedores"

    codigo: Mapped[str] = mapped_column(String(30), primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    telefono: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Proveedor(codigo='{self.codigo}', nombre='{self.nombre}', email='{self.email}')>"
