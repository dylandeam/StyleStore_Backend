"""
Roles and Permissions management endpoints (CU5).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user, require_permission
from app.schemas.role import (
    RoleItemResponse,
    RolePermissionsResponse,
    PermissionResponse,
    UpdateRolePermissionsRequest,
)
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])


@router.get(
    "",
    response_model=list[RoleItemResponse],
    summary="Listar roles",
    description="Obtiene la lista de los 4 roles del sistema y el conteo de permisos asignados a cada uno.",
)
async def list_roles(
    current_user: User = Depends(require_permission("roles.gestionar")),
    db: Session = Depends(get_db),
):
    """Listar roles y conteo de permisos."""
    role_service = RoleService(db)
    # Ensure default permissions are seeded
    role_service.seed_default_permissions_and_roles()
    return role_service.list_roles()


@router.get(
    "/permissions/all",
    response_model=list[PermissionResponse],
    summary="Listar todos los permisos disponibles",
    description="Obtiene el catálogo completo de permisos del sistema.",
)
async def list_all_permissions(
    current_user: User = Depends(require_permission("roles.gestionar")),
    db: Session = Depends(get_db),
):
    """Listar todos los permisos del sistema."""
    role_service = RoleService(db)
    role_service.seed_default_permissions_and_roles()
    return role_service.list_all_permissions()


@router.get(
    "/{role}/permissions",
    response_model=RolePermissionsResponse,
    summary="Obtener permisos de un rol",
    description="Devuelve la lista de permisos asignados a un rol específico.",
)
async def get_role_permissions(
    role: str,
    current_user: User = Depends(require_permission("roles.gestionar")),
    db: Session = Depends(get_db),
):
    """Obtener permisos asignados a un rol."""
    role_service = RoleService(db)
    role_service.seed_default_permissions_and_roles()
    return role_service.get_role_permissions(role)


@router.put(
    "/{role}/permissions",
    response_model=RolePermissionsResponse,
    summary="Actualizar permisos de un rol",
    description="Actualiza la lista de permisos asignados a un rol y lo registra en bitácora.",
)
async def update_role_permissions(
    role: str,
    request: UpdateRolePermissionsRequest,
    current_user: User = Depends(require_permission("roles.gestionar")),
    db: Session = Depends(get_db),
):
    """Actualizar permisos de un rol."""
    role_service = RoleService(db)
    return role_service.update_role_permissions(
        role=role,
        permission_codes=request.permission_codes,
        current_user=current_user,
    )
