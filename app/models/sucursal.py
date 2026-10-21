"""
Sucursal model for Store Branches.
"""
from datetime import datetime
from decimal import Decimal
from datetime import time
from sqlalchemy import String, Boolean, DateTime, Numeric, Integer, ForeignKey, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Sucursal(Base):
    """Branch / Store table."""

    __tablename__ = "sucursales"
    __table_args__ = (
        UniqueConstraint("empresa_id", "name", name="uq_sucursales_empresa_nombre"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    empresa_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    latitud: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    longitud: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    maps_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    hora_apertura: Mapped[time] = mapped_column(Time, default=time(9, 0), nullable=False)
    hora_cierre: Mapped[time] = mapped_column(Time, default=time(18, 0), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    empresa_rel = relationship("Empresa", back_populates="sucursales", lazy="joined")

    @property
    def nombre(self) -> str:
        return self.name

    @property
    def ciudad(self) -> str:
        return self.city

    @property
    def direccion(self) -> str:
        return self.address

    @property
    def telefono(self) -> str:
        return self.phone

    @property
    def ubicacion_url(self) -> str | None:
        return self.maps_url

    @property
    def empresa_nombre(self) -> str | None:
        return self.empresa_rel.nombre if self.empresa_rel else None

    def __repr__(self) -> str:
        return f"<Sucursal(id={self.id}, name='{self.name}', city='{self.city}')>"
