"""
Productos (Product Catalog & Inventory) CRUD endpoints.
Conforme a Especificación StyleStore v4 (Diagrama DB Oficial).
PK: codigo (String(50)).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import require_permission
from app.schemas.producto import ProductoCreate, ProductoUpdate, ProductoResponse
from app.schemas.stock_inventario import StockBulkUpdateRequest, StockInventarioResponse
from app.schemas.common import MessageResponse
from app.services.producto_service import ProductoService
from app.services.stock_service import StockService

router = APIRouter(prefix="/productos", tags=["Productos"])


@router.get(
    "",
    response_model=list[ProductoResponse],
    summary="Listar productos del catálogo",
    description="Devuelve todos los productos con categorías, temporadas, colores y stock total.",
)
async def list_productos(
    active_only: bool = False,
    categoria_id: int | None = None,
    temporada_id: int | None = None,
    sucursal_id: int | None = None,
    search: str | None = None,
    current_user: User = Depends(require_permission("productos.ver")),
    db: Session = Depends(get_db),
):
    service = ProductoService(db)
    return service.list_productos(
        active_only=active_only,
        categoria_id=categoria_id,
        temporada_id=temporada_id,
        sucursal_id=sucursal_id,
        search=search,
    )


@router.get(
    "/{codigo}",
    response_model=ProductoResponse,
    summary="Obtener producto por código",
    description="Devuelve el detalle del producto especificado por su código.",
)
async def get_producto(
    codigo: str,
    current_user: User = Depends(require_permission("productos.ver")),
    db: Session = Depends(get_db),
):
    service = ProductoService(db)
    return service.get_producto_by_codigo(codigo)


@router.post(
    "",
    response_model=ProductoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear producto",
    description="Registra una nueva prenda en el catálogo.",
)
async def create_producto(
    request: ProductoCreate,
    current_user: User = Depends(require_permission("productos.crear")),
    db: Session = Depends(get_db),
):
    service = ProductoService(db)
    return service.create_producto(request, current_user=current_user)


@router.put(
    "/{codigo}",
    response_model=ProductoResponse,
    summary="Actualizar producto",
    description="Modifica los datos de una prenda en el catálogo.",
)
async def update_producto(
    codigo: str,
    request: ProductoUpdate,
    current_user: User = Depends(require_permission("productos.editar")),
    db: Session = Depends(get_db),
):
    service = ProductoService(db)
    return service.update_producto(codigo, request, current_user=current_user)


@router.delete(
    "/{codigo}",
    response_model=MessageResponse,
    summary="Eliminar producto",
    description="Elimina una prenda del catálogo.",
)
async def delete_producto(
    codigo: str,
    current_user: User = Depends(require_permission("productos.eliminar")),
    db: Session = Depends(get_db),
):
    service = ProductoService(db)
    result = service.delete_producto(codigo, current_user=current_user)
    return MessageResponse(message=result["message"])


# --- Endpoints de Stock_Inventario por Producto ---

@router.get(
    "/{codigo}/stock",
    response_model=list[StockInventarioResponse],
    summary="Obtener existencias de stock del producto",
    description="Desglosa las existencias por color, talla y sucursal.",
)
async def get_producto_stock(
    codigo: str,
    current_user: User = Depends(require_permission("productos.ver")),
    db: Session = Depends(get_db),
):
    service = StockService(db)
    return service.get_stock_by_producto(codigo)


@router.post(
    "/{codigo}/stock",
    response_model=list[StockInventarioResponse],
    summary="Actualizar existencias de stock del producto",
    description="Actualiza las cantidades de existencias por color, talla y sucursal.",
)
async def update_producto_stock(
    codigo: str,
    request: StockBulkUpdateRequest,
    current_user: User = Depends(require_permission("productos.editar")),
    db: Session = Depends(get_db),
):
    service = StockService(db)
    return service.update_stock_bulk(codigo, request, current_user=current_user)


@router.post(
    "/{codigo}/analizar-prenda-ia",
    response_model=ProductoResponse,
    summary="Analizar y calibrar puntos clave de la prenda con IA",
    description="Analiza la imagen frontal de la prenda para detectar cuello, hombros, sisas, puños y tipo de manga.",
)
async def analizar_prenda_ia(
    codigo: str,
    current_user: User = Depends(require_permission("productos.editar")),
    db: Session = Depends(get_db),
):
    service = ProductoService(db)
    return service.analizar_y_guardar_puntos_clave(codigo, current_user=current_user)


@router.post(
    "/analizar-imagen-ia",
    summary="Analizar imagen de prenda temporal con IA",
    description="Analiza una imagen recién subida por URL relativa para previsualizar puntos anatómicos y tipo de manga.",
)
async def analizar_imagen_ia(
    payload: dict,
    current_user: User = Depends(require_permission("productos.crear")),
):
    import os
    from app.services.garment_ai_service import GarmentAIService

    img_rel_path = payload.get("foto") or payload.get("foto_vestidor_frontal")
    tipo_prenda = payload.get("tipo_prenda", "superior")
    if not img_rel_path:
        return GarmentAIService.get_fallback_landmarks(tipo_prenda)

    clean_path = img_rel_path.lstrip("/")
    if not clean_path.startswith("uploads"):
        clean_path = os.path.join("uploads", clean_path)
    disk_path = os.path.join(os.getcwd(), clean_path)

    return GarmentAIService.analyze_garment_image(disk_path, tipo_prenda=tipo_prenda)
