"""Memberships that allow a client account to belong to several tenants."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserEmpresa(Base):
    __tablename__ = "user_empresas"
    __table_args__ = (UniqueConstraint("user_id", "empresa_id", name="uq_user_empresa"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    empresa = relationship("Empresa")
