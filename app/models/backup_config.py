"""
Modelo BackupConfig.
Almacena la configuración de periodicidad y retención para copias de seguridad automáticas.
"""
from datetime import datetime
from sqlalchemy import Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BackupConfig(Base):
    """Configuración de copias de seguridad automáticas de StyleStore."""

    __tablename__ = "backup_config"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    auto_backup_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    frequency_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    last_auto_backup: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
