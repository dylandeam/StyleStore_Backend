"""Auditable cash refunds caused by rejected offline sales."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReembolsoOffline(Base):
    __tablename__ = "reembolsos_offline"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    sucursal_id: Mapped[int | None] = mapped_column(ForeignKey("sucursales.id", ondelete="SET NULL"), index=True)
    sync_operation_id: Mapped[int] = mapped_column(ForeignKey("sync_operations.id", ondelete="RESTRICT"), unique=True, nullable=False)
    operation_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="BOB")
    metodo_original: Mapped[str] = mapped_column(String(30), nullable=False, default="efectivo")
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente", index=True)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text)
    procesado_por: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    procesado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sync_operation = relationship("SyncOperation")
