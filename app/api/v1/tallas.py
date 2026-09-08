"""
Endpoints para Tallas (CU13).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import require_permission
from app.schemas.talla import TallaCreate, TallaUpdate, TallaResponse
from app.schemas.common import MessageResponse
from app.services.talla_service import TallaService

router = APIRouter(prefix="/tallas", tags=["Tallas"])


@router.get("", response_model=list[TallaResponse], summary="Listar tallas")
async def list_tallas(
    current_user: User = Depends(require_permission("tallas.ver")),
    db: Session = Depends(get_db),
):
    service = TallaService(db)
    return service.list_tallas()


@router.get("/{talla_id}", response_model=TallaResponse, summary="Obtener talla por ID")
async def get_talla(
    talla_id: int,
    current_user: User = Depends(require_permission("tallas.ver")),
    db: Session = Depends(get_db),
):
    service = TallaService(db)
    return service.get_talla_by_id(talla_id)


@router.post("", response_model=TallaResponse, status_code=status.HTTP_201_CREATED, summary="Crear talla")
async def create_talla(
    request: TallaCreate,
    current_user: User = Depends(require_permission("tallas.crear")),
    db: Session = Depends(get_db),
):
    service = TallaService(db)
    return service.create_talla(request, current_user=current_user)


@router.put("/{talla_id}", response_model=TallaResponse, summary="Actualizar talla")
async def update_talla(
    talla_id: int,
    request: TallaUpdate,
    current_user: User = Depends(require_permission("tallas.editar")),
    db: Session = Depends(get_db),
):
    service = TallaService(db)
    return service.update_talla(talla_id, request, current_user=current_user)


@router.delete("/{talla_id}", response_model=MessageResponse, summary="Eliminar talla")
async def delete_talla(
    talla_id: int,
    current_user: User = Depends(require_permission("tallas.eliminar")),
    db: Session = Depends(get_db),
):
    service = TallaService(db)
    result = service.delete_talla(talla_id, current_user=current_user)
    return MessageResponse(message=result["message"])
