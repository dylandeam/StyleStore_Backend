"""
RolePermission association model.
"""
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RolePermission(Base):
    """Role-Permission mapping table."""

    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    role_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    permission_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )

    role_rel = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")

    def __repr__(self) -> str:
        return f"<RolePermission(id={self.id}, role_id={self.role_id}, role='{self.role}', permission_id={self.permission_id})>"
