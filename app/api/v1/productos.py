"""
Productos (Catalog and Inventory) CRUD endpoints.
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import require_permission
from app.schemas.producto import ProductoCreate, ProductoUpdate, ProductoResponse
from app.schemas.common import MessageResponse
from app.services.producto_service import ProductoService

router = APIRouter(prefix="/productos", tags=["Productos"])


@router.get(
    "",
    response_model=list[ProductoResponse],
    summary="Listar productos",
    description="Obtiene el catálogo de productos con filtros opcionales de búsqueda y categoría.",
)
async def list_productos(
    category: str | None = Query(None, description="Filtrar por categoría"),
    search: str | None = Query(None, description="Buscar por nombre, color o descripción"),
    active_only: bool = Query(False, description="Solo productos activos"),
    current_user: User = Depends(require_permission("productos.ver")),
    db: Session = Depends(get_db),
):
    """Listar productos del catálogo."""
    service = ProductoService(db)
    return service.list_productos(category=category, search=search, active_only=active_only)


@router.get(
    "/{producto_id}",
    response_model=ProductoResponse,
    summary="Obtener producto por ID",
    description="Devuelve el detalle completo de un producto.",
)
async def get_producto(
    producto_id: int,
    current_user: User = Depends(require_permission("productos.ver")),
    db: Session = Depends(get_db),
):
    """Obtener detalle de producto."""
    service = ProductoService(db)
    return service.get_producto_by_id(producto_id)


@router.post(
    "",
    response_model=ProductoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear producto",
    description="Crea un nuevo producto en el catálogo.",
)
async def create_producto(
    request: ProductoCreate,
    current_user: User = Depends(require_permission("productos.crear")),
    db: Session = Depends(get_db),
):
    """Crear producto."""
    service = ProductoService(db)
    return service.create_producto(request, current_user=current_user)


@router.put(
    "/{producto_id}",
    response_model=ProductoResponse,
    summary="Actualizar producto",
    description="Actualiza la información, precio o stock de un producto.",
)
async def update_producto(
    producto_id: int,
    request: ProductoUpdate,
    current_user: User = Depends(require_permission("productos.editar")),
    db: Session = Depends(get_db),
):
    """Actualizar producto."""
    service = ProductoService(db)
    return service.update_producto(producto_id, request, current_user=current_user)


@router.delete(
    "/{producto_id}",
    response_model=MessageResponse,
    summary="Eliminar producto",
    description="Elimina un producto del catálogo.",
)
async def delete_producto(
    producto_id: int,
    current_user: User = Depends(require_permission("productos.eliminar")),
    db: Session = Depends(get_db),
):
    """Eliminar producto."""
    service = ProductoService(db)
    result = service.delete_producto(producto_id, current_user=current_user)
    return MessageResponse(message=result["message"])
