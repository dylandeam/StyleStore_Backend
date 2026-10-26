"""
API endpoints para Promociones y Descuentos (CU Promociones).
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.user import User
from app.schemas.producto import ProductoResponse, PromocionUpdate
from app.services.producto_service import ProductoService
from app.api.deps import get_optional_current_user, require_permission
from app.models.empresa import Empresa
from app.models.categoria import Categoria
from app.models.temporada import Temporada
from app.models.promocion import PromocionAgrupada, CodigoDescuento
from app.schemas.promocion import (
    PromocionAgrupadaCreate, PromocionAgrupadaUpdate,
    CodigoDescuentoCreate, CodigoDescuentoUpdate,
    ValidarCodigoRequest, ValidarCodigoResponse,
)
from app.services.promocion_service import PromocionService
from app.core.exceptions import BadRequestException, NotFoundException
from app.services.tenant_scope import effective_empresa_id

router = APIRouter(prefix="/promociones", tags=["promociones"])


def _empresa_objetivo(current_user: User, empresa_id: int | None = None) -> int:
    if current_user.is_platform_admin:
        objetivo = empresa_id or effective_empresa_id(current_user)
        if not objetivo:
            raise BadRequestException("El administrador SaaS debe indicar empresa_id.")
        return objetivo
    if not current_user.empresa_id:
        raise BadRequestException("Tu usuario no tiene un tenant asociado.")
    if empresa_id and empresa_id != current_user.empresa_id:
        raise NotFoundException("Tenant no encontrado.")
    return current_user.empresa_id


def _promo_dict(item: PromocionAgrupada) -> dict:
    return {
        "id": item.id, "empresa_id": item.empresa_id, "nombre": item.nombre,
        "tipo": item.tipo, "categoria_id": item.categoria_id, "temporada_id": item.temporada_id,
        "categoria_nombre": item.categoria.nombre if item.categoria else None,
        "temporada_nombre": item.temporada.nombre if item.temporada else None,
        "porcentaje": item.porcentaje, "fecha_inicio": item.fecha_inicio,
        "fecha_fin": item.fecha_fin, "active": item.active, "created_at": item.created_at,
    }


def _validar_objetivo(db: Session, empresa_id: int, data) -> None:
    if data.tipo == "categoria":
        existe = db.query(Categoria).filter(Categoria.id == data.categoria_id, Categoria.empresa_id == empresa_id).first()
        if not existe:
            raise BadRequestException("La categoría no pertenece al tenant seleccionado.")
    else:
        existe = db.query(Temporada).filter(Temporada.id == data.temporada_id, Temporada.empresa_id == empresa_id).first()
        if not existe:
            raise BadRequestException("La temporada no pertenece al tenant seleccionado.")


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


@router.get("/agrupadas")
def listar_promociones_agrupadas(
    empresa_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("promociones.gestionar")),
):
    objetivo = _empresa_objetivo(current_user, empresa_id)
    return [_promo_dict(p) for p in db.query(PromocionAgrupada).filter(PromocionAgrupada.empresa_id == objetivo).order_by(PromocionAgrupada.created_at.desc()).all()]


@router.post("/agrupadas", status_code=status.HTTP_201_CREATED)
def crear_promocion_agrupada(
    req: PromocionAgrupadaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("promociones.gestionar")),
):
    empresa_id = _empresa_objetivo(current_user, req.empresa_id)
    _validar_objetivo(db, empresa_id, req)
    item = PromocionAgrupada(**req.model_dump(exclude={"empresa_id"}), empresa_id=empresa_id)
    db.add(item); db.commit(); db.refresh(item)
    return _promo_dict(item)


@router.put("/agrupadas/{promocion_id}")
def actualizar_promocion_agrupada(
    promocion_id: int, req: PromocionAgrupadaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("promociones.gestionar")),
):
    query = db.query(PromocionAgrupada).filter(PromocionAgrupada.id == promocion_id)
    objetivo = effective_empresa_id(current_user)
    if objetivo is not None:
        query = query.filter(PromocionAgrupada.empresa_id == objetivo)
    item = query.first()
    if not item: raise NotFoundException("Promoción agrupada no encontrada.")
    _validar_objetivo(db, item.empresa_id, req)
    for key, value in req.model_dump().items(): setattr(item, key, value)
    db.commit(); db.refresh(item)
    return _promo_dict(item)


@router.delete("/agrupadas/{promocion_id}")
def eliminar_promocion_agrupada(
    promocion_id: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("promociones.gestionar")),
):
    query = db.query(PromocionAgrupada).filter(PromocionAgrupada.id == promocion_id)
    objetivo = effective_empresa_id(current_user)
    if objetivo is not None: query = query.filter(PromocionAgrupada.empresa_id == objetivo)
    item = query.first()
    if not item: raise NotFoundException("Promoción agrupada no encontrada.")
    db.delete(item); db.commit()
    return {"message": "Promoción eliminada."}


@router.get("/codigos")
def listar_codigos(
    empresa_id: int | None = Query(None), db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("promociones.gestionar")),
):
    objetivo = _empresa_objetivo(current_user, empresa_id)
    return db.query(CodigoDescuento).filter(CodigoDescuento.empresa_id == objetivo).order_by(CodigoDescuento.created_at.desc()).all()


@router.post("/codigos", status_code=status.HTTP_201_CREATED)
def crear_codigo(
    req: CodigoDescuentoCreate, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("promociones.gestionar")),
):
    empresa_id = _empresa_objetivo(current_user, req.empresa_id)
    item = CodigoDescuento(**req.model_dump(exclude={"empresa_id"}), empresa_id=empresa_id)
    db.add(item)
    try: db.commit()
    except IntegrityError as exc:
        db.rollback(); raise BadRequestException("Ya existe ese código en el tenant.") from exc
    db.refresh(item); return item


@router.put("/codigos/{codigo_id}")
def actualizar_codigo(
    codigo_id: int, req: CodigoDescuentoUpdate, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("promociones.gestionar")),
):
    query = db.query(CodigoDescuento).filter(CodigoDescuento.id == codigo_id)
    objetivo = effective_empresa_id(current_user)
    if objetivo is not None: query = query.filter(CodigoDescuento.empresa_id == objetivo)
    item = query.first()
    if not item: raise NotFoundException("Código de descuento no encontrado.")
    for key, value in req.model_dump().items(): setattr(item, key, value)
    try: db.commit()
    except IntegrityError as exc:
        db.rollback(); raise BadRequestException("Ya existe ese código en el tenant.") from exc
    db.refresh(item); return item


@router.delete("/codigos/{codigo_id}")
def eliminar_codigo(
    codigo_id: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("promociones.gestionar")),
):
    query = db.query(CodigoDescuento).filter(CodigoDescuento.id == codigo_id)
    objetivo = effective_empresa_id(current_user)
    if objetivo is not None: query = query.filter(CodigoDescuento.empresa_id == objetivo)
    item = query.first()
    if not item: raise NotFoundException("Código de descuento no encontrado.")
    db.delete(item); db.commit(); return {"message": "Código eliminado."}


@router.post("/codigos/validar", response_model=ValidarCodigoResponse)
def validar_codigo(
    req: ValidarCodigoRequest, db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    if not current_user or not current_user.empresa_id:
        raise BadRequestException("Inicia sesión y selecciona un tenant para usar un código.")
    item = PromocionService(db).validar_codigo(current_user.empresa_id, req.codigo, req.canal)
    if not item:
        raise NotFoundException("Código de descuento no encontrado o no disponible.")
    return {"valido": True, "codigo": item.codigo, "porcentaje": item.porcentaje, "descripcion": item.descripcion}
