"""
Endpoints para Categorías (CU11).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import require_permission
from app.schemas.categoria import CategoriaCreate, CategoriaUpdate, CategoriaResponse
from app.schemas.common import MessageResponse
from app.services.categoria_service import CategoriaService

router = APIRouter(prefix="/categorias", tags=["Categorias"])


@router.get("", response_model=list[CategoriaResponse], summary="Listar categorías")
async def list_categorias(
    current_user: User = Depends(require_permission("categorias.ver")),
    db: Session = Depends(get_db),
):
    service = CategoriaService(db)
    return service.list_categorias()


@router.get("/{cat_id}", response_model=CategoriaResponse, summary="Obtener categoría por ID")
async def get_categoria(
    cat_id: int,
    current_user: User = Depends(require_permission("categorias.ver")),
    db: Session = Depends(get_db),
):
    service = CategoriaService(db)
    return service.get_categoria_by_id(cat_id)


@router.post("", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED, summary="Crear categoría")
async def create_categoria(
    request: CategoriaCreate,
    current_user: User = Depends(require_permission("categorias.crear")),
    db: Session = Depends(get_db),
):
    service = CategoriaService(db)
    return service.create_categoria(request, current_user=current_user)


@router.put("/{cat_id}", response_model=CategoriaResponse, summary="Actualizar categoría")
async def update_categoria(
    cat_id: int,
    request: CategoriaUpdate,
    current_user: User = Depends(require_permission("categorias.editar")),
    db: Session = Depends(get_db),
):
    service = CategoriaService(db)
    return service.update_categoria(cat_id, request, current_user=current_user)


@router.delete("/{cat_id}", response_model=MessageResponse, summary="Eliminar categoría")
async def delete_categoria(
    cat_id: int,
    current_user: User = Depends(require_permission("categorias.eliminar")),
    db: Session = Depends(get_db),
):
    service = CategoriaService(db)
    result = service.delete_categoria(cat_id, current_user=current_user)
    return MessageResponse(message=result["message"])
