"""
Endpoints para Proveedores (CU16).
Conforme a Especificación StyleStore v4 (Diagrama DB Oficial).
Sin campo CI según diagrama.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import require_permission
from app.schemas.proveedor import ProveedorCreate, ProveedorUpdate, ProveedorResponse
from app.schemas.common import MessageResponse
from app.services.proveedor_service import ProveedorService

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


@router.get("", response_model=list[ProveedorResponse], summary="Listar proveedores")
async def list_proveedores(
    current_user: User = Depends(require_permission("proveedores.ver")),
    db: Session = Depends(get_db),
):
    service = ProveedorService(db)
    return service.list_proveedores()


@router.get("/{codigo}", response_model=ProveedorResponse, summary="Obtener proveedor por código")
async def get_proveedor(
    codigo: str,
    current_user: User = Depends(require_permission("proveedores.ver")),
    db: Session = Depends(get_db),
):
    service = ProveedorService(db)
    return service.get_proveedor_by_codigo(codigo)


@router.post("", response_model=ProveedorResponse, status_code=status.HTTP_201_CREATED, summary="Crear proveedor")
async def create_proveedor(
    request: ProveedorCreate,
    current_user: User = Depends(require_permission("proveedores.crear")),
    db: Session = Depends(get_db),
):
    service = ProveedorService(db)
    return service.create_proveedor(request, current_user=current_user)


@router.put("/{codigo}", response_model=ProveedorResponse, summary="Actualizar proveedor")
async def update_proveedor(
    codigo: str,
    request: ProveedorUpdate,
    current_user: User = Depends(require_permission("proveedores.editar")),
    db: Session = Depends(get_db),
):
    service = ProveedorService(db)
    return service.update_proveedor(codigo, request, current_user=current_user)


@router.delete("/{codigo}", response_model=MessageResponse, summary="Eliminar proveedor")
async def delete_proveedor(
    codigo: str,
    current_user: User = Depends(require_permission("proveedores.eliminar")),
    db: Session = Depends(get_db),
):
    service = ProveedorService(db)
    result = service.delete_proveedor(codigo, current_user=current_user)
    return MessageResponse(message=result["message"])
