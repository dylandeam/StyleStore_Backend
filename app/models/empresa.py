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
    nombre_marca: Mapped[str | None] = mapped_column(String(150), nullable=True)
    eslogan: Mapped[str | None] = mapped_column(String(220), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    color_primario: Mapped[str] = mapped_column(String(7), default="#14263D", server_default="#14263D", nullable=False)
    color_secundario: Mapped[str] = mapped_column(String(7), default="#FBF8F1", server_default="#FBF8F1", nullable=False)
    color_acento: Mapped[str] = mapped_column(String(7), default="#274C77", server_default="#274C77", nullable=False)
    color_fondo: Mapped[str] = mapped_column(String(7), default="#EEE7D8", server_default="#EEE7D8", nullable=False)
    color_texto: Mapped[str] = mapped_column(String(7), default="#172536", server_default="#172536", nullable=False)
    color_texto_contraste: Mapped[str] = mapped_column(String(7), default="#FFFFFF", server_default="#FFFFFF", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    inactive_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    plazo_cambios_dias: Mapped[int] = mapped_column(Integer, default=7, server_default="7", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="empresa_rel", lazy="select")
    sucursales = relationship("Sucursal", back_populates="empresa_rel", lazy="select")

    def __repr__(self) -> str:
        return f"<Empresa(id={self.id}, codigo='{self.codigo}', nombre='{self.nombre}')>"
