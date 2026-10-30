"""Helpers that enforce the authenticated company's data boundary."""
from sqlalchemy.orm import Query, Session

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.sucursal import Sucursal
from app.models.user import User


def selected_tenant_id(current_user: User) -> int | None:
    """Return the request-scoped tenant selected by the SaaS administrator."""
    value = getattr(current_user, "_selected_empresa_id", None)
    return int(value) if value is not None else None


def effective_empresa_id(current_user: User) -> int | None:
    """Resolve the tenant that must bound this request, or None for a global SaaS view."""
    if current_user.is_platform_admin:
        return selected_tenant_id(current_user)
    return current_user.empresa_id


def require_effective_empresa_id(current_user: User) -> int:
    """Resolve the tenant for a write and reject ambiguous platform-wide writes."""
    empresa_id = effective_empresa_id(current_user)
    if empresa_id is None:
        raise BadRequestException(
            "Selecciona un tenant antes de crear o modificar información del catálogo."
        )
    return empresa_id


def scoped_sucursal_ids(db: Session, current_user: User):
    """Return a SQL subquery containing only branches visible to the user."""
    query = db.query(Sucursal.id)
    empresa_id = effective_empresa_id(current_user)
    if empresa_id is not None:
        query = query.filter(Sucursal.empresa_id == empresa_id)
    return query


def scope_by_sucursal(query: Query, db: Session, current_user: User, column):
    """Apply tenant scope to a resource related to a branch."""
    if effective_empresa_id(current_user) is None:
        return query
    return query.filter(column.in_(scoped_sucursal_ids(db, current_user)))


def scope_by_empresa(query: Query, current_user: User, column):
    """Apply tenant scope to a resource that owns an empresa_id column."""
    empresa_id = effective_empresa_id(current_user)
    if empresa_id is None:
        return query
    return query.filter(column == empresa_id)


def get_scoped_sucursal(db: Session, current_user: User, sucursal_id: int) -> Sucursal:
    """Resolve a branch without revealing whether a foreign tenant branch exists."""
    query = db.query(Sucursal).filter(Sucursal.id == sucursal_id)
    empresa_id = effective_empresa_id(current_user)
    if empresa_id is not None:
        query = query.filter(Sucursal.empresa_id == empresa_id)
    sucursal = query.first()
    if not sucursal:
        raise NotFoundException(f"Sucursal con ID {sucursal_id} no encontrada.")
    return sucursal
