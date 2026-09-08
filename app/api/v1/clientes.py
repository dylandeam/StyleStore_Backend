"""
Endpoints para Clientes (CU9).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import require_permission
from app.schemas.cliente import ClienteCreate, ClienteUpdate, ClienteResponse
from app.schemas.common import MessageResponse
from app.services.cliente_service import ClienteService

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("", response_model=list[ClienteResponse], summary="Listar clientes")
async def list_clientes(
    current_user: User = Depends(require_permission("clientes.ver")),
    db: Session = Depends(get_db),
):
    service = ClienteService(db)
    return service.list_clientes()


@router.get("/{codigo}", response_model=ClienteResponse, summary="Obtener cliente por código")
async def get_cliente(
    codigo: str,
    current_user: User = Depends(require_permission("clientes.ver")),
    db: Session = Depends(get_db),
):
    service = ClienteService(db)
    return service.get_cliente_by_codigo(codigo)


@router.post("", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED, summary="Crear cliente")
async def create_cliente(
    request: ClienteCreate,
    current_user: User = Depends(require_permission("clientes.crear")),
    db: Session = Depends(get_db),
):
    service = ClienteService(db)
    return service.create_cliente(request, current_user=current_user)


@router.put("/{codigo}", response_model=ClienteResponse, summary="Actualizar cliente")
async def update_cliente(
    codigo: str,
    request: ClienteUpdate,
    current_user: User = Depends(require_permission("clientes.editar")),
    db: Session = Depends(get_db),
):
    service = ClienteService(db)
    return service.update_cliente(codigo, request, current_user=current_user)


@router.delete("/{codigo}", response_model=MessageResponse, summary="Eliminar cliente")
async def delete_cliente(
    codigo: str,
    current_user: User = Depends(require_permission("clientes.eliminar")),
    db: Session = Depends(get_db),
):
    service = ClienteService(db)
    result = service.delete_cliente(codigo, current_user=current_user)
    return MessageResponse(message=result["message"])
