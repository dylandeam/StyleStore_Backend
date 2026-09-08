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

    def __init__(self, db: Session | None = None):
        self.db = db

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

    def registrar_accion(
        self,
        action: str,
        module: str | None = None,
        user: User | str | None = None,
        user_id: int | None = None,
        user_snapshot: str | None = None,
        db: Session | None = None,
    ) -> Bitacora:
        """Helper para registrar acciones cuando el servicio ya fue instanciado con db."""
        target_db = db or self.db
        if not target_db:
            raise ValueError("No database session provided to registrar_accion")

        if user is not None:
            return self.registrar(db=target_db, user=user, action=action, module=module)

        log_entry = Bitacora(
            user_id=user_id,
            user_snapshot=user_snapshot or "Sistema",
            action=action,
            module=module,
        )
        target_db.add(log_entry)
        target_db.commit()
        target_db.refresh(log_entry)
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
