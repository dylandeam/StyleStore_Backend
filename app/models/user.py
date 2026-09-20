"""
User model for SQLAlchemy.
"""
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """User table in the database."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ci: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    foto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="cliente", server_default="cliente")
    developer_key_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bitacora_password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    role_rel = relationship("Role", back_populates="users", lazy="joined")

    @property
    def sucursal_id(self) -> int | None:
        try:
            from app.models.empleado import Empleado
            # Chequear relación si fue cargada
            if hasattr(self, "empleado_rel") and self.empleado_rel:
                emp = self.empleado_rel[0] if isinstance(self.empleado_rel, list) else self.empleado_rel
                return getattr(emp, "sucursal_id", None)
        except Exception:
            pass
        return None

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}', role='{self.role}')>"
