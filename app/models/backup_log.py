"""
Modelo BackupLog.
Registro de copias de seguridad del sistema StyleStore con hash SHA-256.
"""
from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BackupLog(Base):
    """Tabla de auditoría de copias de seguridad (Backups)."""

    __tablename__ = "backup_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tamano_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")  # 'manual', 'automatico'
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="exitoso")  # 'exitoso', 'fallido'
    creado_por_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relaciones
    usuario = relationship("User")

    def __repr__(self) -> str:
        return f"<BackupLog(id={self.id}, archivo='{self.nombre_archivo}', sha256='{self.sha256_hash[:8]}...')>"
