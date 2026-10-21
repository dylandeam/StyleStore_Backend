"""Empresa (tenant) model for the multi-company SaaS boundary."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Empresa(Base):
    """Contracting company that owns users, branches and business data."""

    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    inactive_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    plazo_cambios_dias: Mapped[int] = mapped_column(Integer, default=7, server_default="7", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="empresa_rel", lazy="select")
    sucursales = relationship("Sucursal", back_populates="empresa_rel", lazy="select")

    def __repr__(self) -> str:
        return f"<Empresa(id={self.id}, codigo='{self.codigo}', nombre='{self.nombre}')>"
