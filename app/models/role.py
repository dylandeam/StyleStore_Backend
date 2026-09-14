"""
Modelo Role para RBAC dinámico (CU5 / v5).
"""
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(Base):
    """Tabla de Roles dinámicos del sistema."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    role_permissions = relationship("RolePermission", back_populates="role_rel", cascade="all, delete-orphan", lazy="selectin")
    users = relationship("User", back_populates="role_rel", lazy="select")

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, nombre='{self.nombre}')>"
