"""
API endpoints para Promociones y Descuentos (CU Promociones).
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.producto import ProductoResponse, PromocionUpdate
from app.services.producto_service import ProductoService
from app.api.deps import get_optional_current_user, require_permission
from app.models.empresa import Empresa

router = APIRouter(prefix="/promociones", tags=["promociones"])


@router.get("", response_model=list[ProductoResponse])
def get_promociones_activas(
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Retorna el listado de productos activos que se encuentran en promoción/descuento."""
    service = ProductoService(db)
    default_empresa = None
    if current_user is None:
        default_empresa = db.query(Empresa).filter(Empresa.codigo == "stylestore").first()
    return service.list_promociones(
        solo_en_promocion=True,
        current_user=current_user,
        empresa_id=default_empresa.id if default_empresa else None,
    )


@router.get("/todas", response_model=list[ProductoResponse])
def get_todas_las_promociones(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("promociones.gestionar")),
):
    """Retorna todos los productos para la consola de gestión de promociones de administración."""
    service = ProductoService(db)
    return service.list_promociones(solo_en_promocion=False, current_user=current_user)


@router.put("/{codigo}", response_model=ProductoResponse)
def actualizar_promocion_producto(
    codigo: str,
    req: PromocionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("promociones.gestionar")),
):
    """Actualiza la promoción o descuento de una prenda del catálogo."""
    service = ProductoService(db)
    return service.update_promocion(codigo=codigo, req=req, current_user=current_user)
