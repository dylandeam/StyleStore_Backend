"""
Endpoints para Empleados (CU8).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import require_permission
from app.schemas.empleado import EmpleadoCreate, EmpleadoUpdate, EmpleadoResponse
from app.schemas.common import MessageResponse
from app.services.empleado_service import EmpleadoService

router = APIRouter(prefix="/empleados", tags=["Empleados"])


@router.get("", response_model=list[EmpleadoResponse], summary="Listar empleados")
async def list_empleados(
    current_user: User = Depends(require_permission("empleados.ver")),
    db: Session = Depends(get_db),
):
    service = EmpleadoService(db)
    return service.list_empleados()


@router.get("/{codigo}", response_model=EmpleadoResponse, summary="Obtener empleado por código")
async def get_empleado(
    codigo: str,
    current_user: User = Depends(require_permission("empleados.ver")),
    db: Session = Depends(get_db),
):
    service = EmpleadoService(db)
    return service.get_empleado_by_codigo(codigo)


@router.post("", response_model=EmpleadoResponse, status_code=status.HTTP_201_CREATED, summary="Crear empleado")
async def create_empleado(
    request: EmpleadoCreate,
    current_user: User = Depends(require_permission("empleados.crear")),
    db: Session = Depends(get_db),
):
    service = EmpleadoService(db)
    return service.create_empleado(request, current_user=current_user)


@router.put("/{codigo}", response_model=EmpleadoResponse, summary="Actualizar empleado")
async def update_empleado(
    codigo: str,
    request: EmpleadoUpdate,
    current_user: User = Depends(require_permission("empleados.editar")),
    db: Session = Depends(get_db),
):
    service = EmpleadoService(db)
    return service.update_empleado(codigo, request, current_user=current_user)


@router.delete("/{codigo}", response_model=MessageResponse, summary="Eliminar empleado")
async def delete_empleado(
    codigo: str,
    current_user: User = Depends(require_permission("empleados.eliminar")),
    db: Session = Depends(get_db),
):
    service = EmpleadoService(db)
    result = service.delete_empleado(codigo, current_user=current_user)
    return MessageResponse(message=result["message"])
