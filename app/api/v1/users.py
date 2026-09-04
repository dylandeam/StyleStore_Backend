"""
User endpoints: profile, employee creation (CU1), listing.
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserCreateByAdmin, UserUpdateByAdmin
from app.api.deps import get_current_user, require_permission
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener perfil actual",
    description="Devuelve el perfil del usuario autenticado actual.",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return current_user


@router.get(
    "",
    response_model=list[UserResponse],
    summary="Listar usuarios y empleados",
    description="Obtiene la lista de usuarios con filtros opcionales de búsqueda y rol.",
)
async def list_users(
    search: str | None = Query(None, description="Buscar por nombre o correo"),
    role: str | None = Query(None, description="Filtrar por rol"),
    current_user: User = Depends(require_permission("usuarios.ver")),
    db: Session = Depends(get_db),
):
    """Listar usuarios del sistema."""
    service = UserService(db)
    return service.list_users(search=search, role=role)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear empleado con rol (CU1)",
    description="Registra un nuevo empleado asignándole un rol específico (cajero, encargado_sucursal, administrador).",
)
async def create_employee(
    request: UserCreateByAdmin,
    current_user: User = Depends(require_permission("usuarios.crear")),
    db: Session = Depends(get_db),
):
    """Crear cuenta de empleado."""
    service = UserService(db)
    return service.create_employee(request, current_user=current_user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Actualizar empleado / usuario",
    description="Permite a un administrador actualizar el rol o estado activo de un usuario.",
)
async def update_user(
    user_id: int,
    request: UserUpdateByAdmin,
    current_user: User = Depends(require_permission("usuarios.crear")),
    db: Session = Depends(get_db),
):
    """Actualizar datos de usuario por parte de un administrador."""
    service = UserService(db)
    return service.update_user_by_admin(user_id, request, current_user=current_user)
