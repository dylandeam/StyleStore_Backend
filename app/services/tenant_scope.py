"""Helpers that enforce the authenticated company's data boundary."""
from sqlalchemy.orm import Query, Session

from app.core.exceptions import NotFoundException
from app.models.sucursal import Sucursal
from app.models.user import User


def scoped_sucursal_ids(db: Session, current_user: User):
    """Return a SQL subquery containing only branches visible to the user."""
    query = db.query(Sucursal.id)
    if not current_user.is_platform_admin:
        query = query.filter(Sucursal.empresa_id == current_user.empresa_id)
    return query


def scope_by_sucursal(query: Query, db: Session, current_user: User, column):
    """Apply tenant scope to a resource related to a branch."""
    if current_user.is_platform_admin:
        return query
    return query.filter(column.in_(scoped_sucursal_ids(db, current_user)))


def get_scoped_sucursal(db: Session, current_user: User, sucursal_id: int) -> Sucursal:
    """Resolve a branch without revealing whether a foreign tenant branch exists."""
    query = db.query(Sucursal).filter(Sucursal.id == sucursal_id)
    if not current_user.is_platform_admin:
        query = query.filter(Sucursal.empresa_id == current_user.empresa_id)
    sucursal = query.first()
    if not sucursal:
        raise NotFoundException(f"Sucursal con ID {sucursal_id} no encontrada.")
    return sucursal
