"""
Modelo QRPagoConfig.
Almacena la imagen y configuración del QR de cobro presencial en mostrador (QR Simple).
"""
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class QRPagoConfig(Base):
    """Configuración del QR de cobro para caja POS."""

    __tablename__ = "qr_pago_config"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    imagen_url: Mapped[str] = mapped_column(String(500), nullable=False)
    banco_destino: Mapped[str | None] = mapped_column(String(100), nullable=True, default="QR Simple BNB / BCP / Banco Unión")
    titular: Mapped[str | None] = mapped_column(String(150), nullable=True, default="StyleStore Bolivia")
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sucursal_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
