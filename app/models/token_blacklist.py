"""
Token blacklist model for tracking revoked JWT tokens.
"""
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TokenBlacklist(Base):
    """Stores revoked JWT tokens to support logout functionality."""

    __tablename__ = "token_blacklist"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    token: Mapped[str] = mapped_column(
        String(500), unique=True, index=True, nullable=False
    )
    blacklisted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<TokenBlacklist(id={self.id}, token='{self.token[:20]}...')>"
