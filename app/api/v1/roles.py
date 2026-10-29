"""
Roles and Permissions management endpoints (CU5 / v5).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user, require_permission
from app.schemas.role import (
    RoleItemResponse,
    RolePermissionsResponse,
    PermissionResponse,
    RoleCreateRequest,
    RoleUpdateRequest,
    UpdateRolePermissionsRequest,
    EffectivePermissionsResponse,
)
from app.services.role_service import RoleService
from app.services.tenant_scope import effective_empresa_id

router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])


def _management_empresa_id(current_user: User) -> int | None:
    return effective_empresa_id(current_user) or current_user.empresa_id


@router.get(
    "/me/permissions",
    response_model=EffectivePermissionsResponse,
    summary="Consultar permisos efectivos del usuario actual",
)
async def get_my_effective_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_service = RoleService(db, current_user.empresa_id)
    return {
        "empresa_id": current_user.empresa_id,
        "role": current_user.role,
        "permission_codes": role_service.effective_permission_codes(current_user),
    }


@router.get(
    "",
    response_model=list[RoleItemResponse],
    summary="Listar roles",
    description="Obtiene la lista de roles del sistema y el conteo de permisos y usuarios asignados a cada uno.",
)
async def list_roles(
    current_user: User = Depends(require_permission("roles.ver")),
    db: Session = Depends(get_db),
):
    """Listar roles y conteo de permisos."""
    role_service = RoleService(db, _management_empresa_id(current_user))
    role_service.seed_default_permissions_and_roles()
    return role_service.list_roles()


@router.post(
    "",
    response_model=RoleItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo rol",
    description="Crea un rol dinámico en el sistema.",
)
async def create_role(
    payload: RoleCreateRequest,
    current_user: User = Depends(require_permission("roles.crear")),
    db: Session = Depends(get_db),
):
    """Crear un rol dinámico."""
    role_service = RoleService(db, _management_empresa_id(current_user))
    role = role_service.create_role(
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        current_user=current_user,
    )
    return {
        "id": role.id,
        "nombre": role.nombre,
        "descripcion": role.descripcion,
        "active": role.active,
        "role": role_service.slug(role.nombre),
        "permission_count": 0,
        "user_count": 0,
        "created_at": role.created_at,
    }


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
    role_service = RoleService(db, _management_empresa_id(current_user))
    role_service.seed_default_permissions_and_roles()
    return role_service.list_all_permissions()


@router.get(
    "/{role_id_or_name}/permissions",
    response_model=RolePermissionsResponse,
    summary="Obtener permisos de un rol",
    description="Devuelve la lista de permisos asignados a un rol específico (por ID o identificador).",
)
async def get_role_permissions(
    role_id_or_name: str,
    current_user: User = Depends(require_permission("roles.gestionar")),
    db: Session = Depends(get_db),
):
    """Obtener permisos asignados a un rol."""
    role_service = RoleService(db, _management_empresa_id(current_user))
    role_service.seed_default_permissions_and_roles()
    return role_service.get_role_permissions(role_id_or_name)


@router.put(
    "/{role_id_or_name}/permissions",
    response_model=RolePermissionsResponse,
    summary="Actualizar permisos de un rol",
    description="Actualiza la lista de permisos asignados a un rol.",
)
async def update_role_permissions(
    role_id_or_name: str,
    payload: UpdateRolePermissionsRequest,
    current_user: User = Depends(require_permission("roles.gestionar")),
    db: Session = Depends(get_db),
):
    """Actualizar permisos de un rol."""
    role_service = RoleService(db, _management_empresa_id(current_user))
    return role_service.update_role_permissions(
        role_id_or_name=role_id_or_name,
        permission_codes=payload.permission_codes,
        current_user=current_user,
    )


@router.put(
    "/{role_id}",
    response_model=RoleItemResponse,
    summary="Editar información de un rol",
    description="Actualiza el nombre, descripción o estado activo de un rol.",
)
async def update_role(
    role_id: int,
    payload: RoleUpdateRequest,
    current_user: User = Depends(require_permission("roles.editar")),
    db: Session = Depends(get_db),
):
    """Editar información de un rol."""
    role_service = RoleService(db, _management_empresa_id(current_user))
    role = role_service.update_role(
        role_id=role_id,
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        active=payload.active,
        current_user=current_user,
    )
    return {
        "id": role.id,
        "nombre": role.nombre,
        "descripcion": role.descripcion,
        "active": role.active,
        "role": role_service.slug(role.nombre),
        "permission_count": len(role.role_permissions),
        "user_count": len(role.users),
        "created_at": role.created_at,
    }


@router.delete(
    "/{role_id}",
    summary="Eliminar un rol",
    description="Elimina un rol siempre que no tenga usuarios asignados.",
)
async def delete_role(
    role_id: int,
    current_user: User = Depends(require_permission("roles.eliminar")),
    db: Session = Depends(get_db),
):
    """Eliminar un rol."""
    role_service = RoleService(db, _management_empresa_id(current_user))
    return role_service.delete_role(role_id=role_id, current_user=current_user)
