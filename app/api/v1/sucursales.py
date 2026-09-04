"""
Sucursales (Store Branches) CRUD endpoints.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import require_permission
from app.schemas.sucursal import SucursalCreate, SucursalUpdate, SucursalResponse
from app.schemas.common import MessageResponse
from app.services.sucursal_service import SucursalService

router = APIRouter(prefix="/sucursales", tags=["Sucursales"])


@router.get(
    "",
    response_model=list[SucursalResponse],
    summary="Listar sucursales",
    description="Obtiene todas las sucursales de la tienda.",
)
async def list_sucursales(
    active_only: bool = False,
    current_user: User = Depends(require_permission("sucursales.ver")),
    db: Session = Depends(get_db),
):
    """Listar todas las sucursales."""
    service = SucursalService(db)
    return service.list_sucursales(active_only=active_only)


@router.get(
    "/{sucursal_id}",
    response_model=SucursalResponse,
    summary="Obtener sucursal por ID",
    description="Devuelve la información detallada de una sucursal.",
)
async def get_sucursal(
    sucursal_id: int,
    current_user: User = Depends(require_permission("sucursales.ver")),
    db: Session = Depends(get_db),
):
    """Obtener detalle de sucursal."""
    service = SucursalService(db)
    return service.get_sucursal_by_id(sucursal_id)


@router.post(
    "",
    response_model=SucursalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear sucursal",
    description="Registra una nueva sucursal física en el sistema.",
)
async def create_sucursal(
    request: SucursalCreate,
    current_user: User = Depends(require_permission("sucursales.crear")),
    db: Session = Depends(get_db),
):
    """Crear nueva sucursal."""
    service = SucursalService(db)
    return service.create_sucursal(request, current_user=current_user)


@router.put(
    "/{sucursal_id}",
    response_model=SucursalResponse,
    summary="Actualizar sucursal",
    description="Modifica los datos de una sucursal existente.",
)
async def update_sucursal(
    sucursal_id: int,
    request: SucursalUpdate,
    current_user: User = Depends(require_permission("sucursales.editar")),
    db: Session = Depends(get_db),
):
    """Actualizar sucursal."""
    service = SucursalService(db)
    return service.update_sucursal(sucursal_id, request, current_user=current_user)


@router.delete(
    "/{sucursal_id}",
    response_model=MessageResponse,
    summary="Eliminar sucursal",
    description="Elimina una sucursal del sistema.",
)
async def delete_sucursal(
    sucursal_id: int,
    current_user: User = Depends(require_permission("sucursales.eliminar")),
    db: Session = Depends(get_db),
):
    """Eliminar sucursal."""
    service = SucursalService(db)
    result = service.delete_sucursal(sucursal_id, current_user=current_user)
    return MessageResponse(message=result["message"])
