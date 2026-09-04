"""
Shared API dependencies — authentication helpers.
"""
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.security import decode_token
from app.core.exceptions import (
    CredentialsException,
    InvalidTokenException,
    ForbiddenException,
)
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.services.auth_service import AuthService
from app.services.user_service import UserService

# HTTP Bearer scheme for extracting tokens from Authorization header
security = HTTPBearer()


async def get_current_user(
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

    if not user.is_active:
        raise CredentialsException(detail="User account is deactivated")

    return user


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
        if current_user.role == "administrador":
            return current_user

        has_perm = (
            db.query(RolePermission)
            .join(Permission, RolePermission.permission_id == Permission.id)
            .filter(
                RolePermission.role == current_user.role,
                Permission.code == permission_code,
            )
            .first()
        )
        if not has_perm:
            raise ForbiddenException(f"No tiene el permiso requerido: '{permission_code}'")
        return current_user

    return permission_checker

