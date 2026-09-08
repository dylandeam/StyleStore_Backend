"""
Endpoints para Colores (CU12).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import require_permission
from app.schemas.color import ColorCreate, ColorUpdate, ColorResponse
from app.schemas.common import MessageResponse
from app.services.color_service import ColorService

router = APIRouter(prefix="/colores", tags=["Colores"])


@router.get("", response_model=list[ColorResponse], summary="Listar colores")
async def list_colores(
    current_user: User = Depends(require_permission("colores.ver")),
    db: Session = Depends(get_db),
):
    service = ColorService(db)
    return service.list_colores()


@router.get("/{color_id}", response_model=ColorResponse, summary="Obtener color por ID")
async def get_color(
    color_id: int,
    current_user: User = Depends(require_permission("colores.ver")),
    db: Session = Depends(get_db),
):
    service = ColorService(db)
    return service.get_color_by_id(color_id)


@router.post("", response_model=ColorResponse, status_code=status.HTTP_201_CREATED, summary="Crear color")
async def create_color(
    request: ColorCreate,
    current_user: User = Depends(require_permission("colores.crear")),
    db: Session = Depends(get_db),
):
    service = ColorService(db)
    return service.create_color(request, current_user=current_user)


@router.put("/{color_id}", response_model=ColorResponse, summary="Actualizar color")
async def update_color(
    color_id: int,
    request: ColorUpdate,
    current_user: User = Depends(require_permission("colores.editar")),
    db: Session = Depends(get_db),
):
    service = ColorService(db)
    return service.update_color(color_id, request, current_user=current_user)


@router.delete("/{color_id}", response_model=MessageResponse, summary="Eliminar color")
async def delete_color(
    color_id: int,
    current_user: User = Depends(require_permission("colores.eliminar")),
    db: Session = Depends(get_db),
):
    service = ColorService(db)
    result = service.delete_color(color_id, current_user=current_user)
    return MessageResponse(message=result["message"])
