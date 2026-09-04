"""
Bitacora (Audit Log) Service.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.bitacora import Bitacora
from app.models.user import User


class BitacoraService:
    """Service for registering and querying system audit logs."""

    @staticmethod
    def registrar(
        db: Session,
        user: User | str | None,
        action: str,
        module: str | None = None,
    ) -> Bitacora:
        """
        Record an action in the audit log.
        - user: User instance, string (email/identifier), or None for system events.
        """
        user_id = None
        if isinstance(user, User):
            user_id = user.id
            user_snapshot = f"{user.name} ({user.email})"
        elif isinstance(user, str):
            user_snapshot = user
        else:
            user_snapshot = "Sistema"

        log_entry = Bitacora(
            user_id=user_id,
            user_snapshot=user_snapshot,
            action=action,
            module=module,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    def list_logs(
        self,
        db: Session,
        user_query: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        module: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        """Retrieve paginated audit logs with optional filters."""
        query = db.query(Bitacora)

        if user_query:
            query = query.filter(Bitacora.user_snapshot.ilike(f"%{user_query}%"))
        if module:
            query = query.filter(Bitacora.module == module)
        if from_date:
            query = query.filter(Bitacora.created_at >= from_date)
        if to_date:
            query = query.filter(Bitacora.created_at <= to_date)

        total = query.count()
        pages = (total + size - 1) // size if total > 0 else 1
        offset = (page - 1) * size

        items = query.order_by(desc(Bitacora.created_at)).offset(offset).limit(size).all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
        }
