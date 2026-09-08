"""
Endpoints para Temporadas (CU14).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import require_permission
from app.schemas.temporada import TemporadaCreate, TemporadaUpdate, TemporadaResponse
from app.schemas.common import MessageResponse
from app.services.temporada_service import TemporadaService

router = APIRouter(prefix="/temporadas", tags=["Temporadas"])


@router.get("", response_model=list[TemporadaResponse], summary="Listar temporadas")
async def list_temporadas(
    current_user: User = Depends(require_permission("temporadas.ver")),
    db: Session = Depends(get_db),
):
    service = TemporadaService(db)
    return service.list_temporadas()


@router.get("/{temp_id}", response_model=TemporadaResponse, summary="Obtener temporada por ID")
async def get_temporada(
    temp_id: int,
    current_user: User = Depends(require_permission("temporadas.ver")),
    db: Session = Depends(get_db),
):
    service = TemporadaService(db)
    return service.get_temporada_by_id(temp_id)


@router.post("", response_model=TemporadaResponse, status_code=status.HTTP_201_CREATED, summary="Crear temporada")
async def create_temporada(
    request: TemporadaCreate,
    current_user: User = Depends(require_permission("temporadas.crear")),
    db: Session = Depends(get_db),
):
    service = TemporadaService(db)
    return service.create_temporada(request, current_user=current_user)


@router.put("/{temp_id}", response_model=TemporadaResponse, summary="Actualizar temporada")
async def update_temporada(
    temp_id: int,
    request: TemporadaUpdate,
    current_user: User = Depends(require_permission("temporadas.editar")),
    db: Session = Depends(get_db),
):
    service = TemporadaService(db)
    return service.update_temporada(temp_id, request, current_user=current_user)


@router.delete("/{temp_id}", response_model=MessageResponse, summary="Eliminar temporada")
async def delete_temporada(
    temp_id: int,
    current_user: User = Depends(require_permission("temporadas.eliminar")),
    db: Session = Depends(get_db),
):
    service = TemporadaService(db)
    result = service.delete_temporada(temp_id, current_user=current_user)
    return MessageResponse(message=result["message"])
