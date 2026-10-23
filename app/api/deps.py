"""
Shared API dependencies — authentication helpers.
"""
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.database import get_db
from app.models.user import User
from app.models.user_empresa import UserEmpresa
from app.core.security import decode_token
from app.core.exceptions import (
    CredentialsException,
    InvalidTokenException,
    ForbiddenException,
)
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.services.auth_service import AuthService
from app.services.plan_service import PlanService
from app.services.user_service import UserService

# HTTP Bearer scheme for extracting tokens from Authorization header
security = HTTPBearer()


def _apply_token_tenant_scope(db: Session, user: User, payload: dict) -> User:
    """Apply a validated JWT tenant to this request without mutating users.empresa_id."""
    token_empresa_id = payload.get("empresa_id")
    if token_empresa_id is None or user.is_platform_admin:
        return user
    try:
        empresa_id = int(token_empresa_id)
    except (TypeError, ValueError) as exc:
        raise CredentialsException(detail="El ámbito de empresa del token no es válido") from exc
    if empresa_id != user.empresa_id:
        membership = db.query(UserEmpresa.id).filter(
            UserEmpresa.user_id == user.id,
            UserEmpresa.empresa_id == empresa_id,
            UserEmpresa.active.is_(True),
        ).first()
        if not membership:
            raise CredentialsException(detail="El ámbito de empresa del token ya no es válido")
    # The entity lives only for this request/session. Marking it as committed prevents
    # an unrelated db.commit() from persisting the selected tenant on the account.
    set_committed_value(user, "empresa_id", empresa_id)
    return user


def _renewal_access_allowed(request: Request, user: User) -> bool:
    """Keep only the minimum account surface available to an expired tenant admin."""
    path = request.url.path.rstrip("/")
    if path in {"/api/v1/auth/tenants", "/api/v1/auth/tenants/select"}:
        return True
    if user.role != "administrador":
        return False
    return path.startswith("/api/v1/planes") or (
        request.method == "GET" and path == "/api/v1/users/me"
    )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that extracts and validates the JWT from the Authorization header,
    checks if the token is blacklisted, and returns the authenticated user.
    """
    token = credentials.credentials

    # Check if token is blacklisted
    auth_service = AuthService(db)
    if auth_service.is_token_blacklisted(token):
        raise InvalidTokenException()

    # Decode and validate token
    payload = decode_token(token)
    if payload is None:
        raise CredentialsException()

    # Check token type
    if payload.get("type") != "access":
        raise CredentialsException(detail="Invalid token type. Expected access token.")

    # Extract user ID from token
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise CredentialsException()

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise CredentialsException()

    # Fetch user from database
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)

    user = _apply_token_tenant_scope(db, user, payload)

    if not user.is_active:
        raise CredentialsException(detail="User account is deactivated")

    if not user.is_platform_admin and user.empresa_id is not None:
        empresa, _ = PlanService(db).reconcile_tenant_access(user.empresa_id)
        if empresa is None or not empresa.active:
            if (
                empresa is not None
                and empresa.inactive_reason == "subscription_expired"
                and _renewal_access_allowed(request, user)
            ):
                return user
            if empresa is not None and empresa.inactive_reason == "subscription_expired":
                raise ForbiddenException(
                    "La suscripción venció. El tenant está inactivo hasta renovar y confirmar el pago."
                )
            raise CredentialsException(detail="La empresa se encuentra suspendida")

    return user


async def require_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    """Allow only the platform operator; tenant administrators are intentionally excluded."""
    if not current_user.is_platform_admin:
        raise ForbiddenException("Esta operación requiere administración global de la plataforma")
    return current_user


optional_security = HTTPBearer(auto_error=False)


async def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
) -> User | None:
    """Extrae el usuario autenticado si el token JWT es provisto y válido; retorna None si es anónimo."""
    if not credentials:
        return None
    try:
        token = credentials.credentials
        auth_service = AuthService(db)
        if auth_service.is_token_blacklisted(token):
            return None
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = int(user_id_str)
        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)
        user = _apply_token_tenant_scope(db, user, payload)
        if user and user.is_active:
            if not user.is_platform_admin and user.empresa_id is not None:
                empresa, _ = PlanService(db).reconcile_tenant_access(user.empresa_id)
                if not empresa.active:
                    if (
                        empresa.inactive_reason == "subscription_expired"
                        and _renewal_access_allowed(request, user)
                    ):
                        return user
                    if empresa.inactive_reason == "subscription_expired":
                        raise ForbiddenException(
                            "La suscripción venció. El tenant está inactivo hasta renovar y confirmar el pago."
                        )
                    raise CredentialsException(detail="La empresa se encuentra suspendida")
            return user
    except CredentialsException:
        raise
    except Exception:
        return None
    return None


def require_role(*roles: str):
    """Dependency that checks if the authenticated user has one of the allowed roles."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role in roles or current_user.role == "administrador":
            return current_user
        raise ForbiddenException("No tiene permisos de rol suficientes para realizar esta acción")

    return role_checker


def require_permission(permission_code: str):
    """Dependency that checks if the authenticated user's role has a specific permission."""
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if current_user.role in ["administrador", "encargado_sucursal"]:
            return current_user

        query_filter = [Permission.code == permission_code]
        if current_user.role_id:
            query_filter.append((RolePermission.role_id == current_user.role_id) | (RolePermission.role == current_user.role))
        else:
            query_filter.append(RolePermission.role == current_user.role)

        has_perm = (
            db.query(RolePermission)
            .join(Permission, RolePermission.permission_id == Permission.id)
            .filter(*query_filter)
            .first()
        )
        if not has_perm:
            raise ForbiddenException(f"No tiene el permiso requerido: '{permission_code}'")
        return current_user

    return permission_checker


def require_plan_capability(capability: str):
    """Enforce the active tenant subscription for a protected operation."""
    async def capability_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        from app.services.plan_service import PlanService

        PlanService(db).require_capability(current_user, capability)
        return current_user

    return capability_checker
