"""
Modelo para almacenamiento persistente de archivos subidos en base de datos.
Evita la pérdida de fotos al reiniciar o redesplegar contenedores en Railway.
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, LargeBinary, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UploadedFile(Base):
    """Tabla para persistencia de fotos de productos y empleados."""

    __tablename__ = "uploaded_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    folder: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(80), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
