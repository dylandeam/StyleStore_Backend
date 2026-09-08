"""
Modelo Cliente (CU9).
Sin campo foto según diagrama oficial v4.
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Cliente(Base):
    """Tabla de Clientes del sistema."""

    __tablename__ = "clientes"

    codigo: Mapped[str] = mapped_column(String(30), primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    telefono: Mapped[str] = mapped_column(String(20), nullable=False)
    direccion: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", backref="cliente_rel", lazy="joined")

    def __repr__(self) -> str:
        return f"<Cliente(codigo='{self.codigo}', user_id={self.user_id}, telefono='{self.telefono}')>"
