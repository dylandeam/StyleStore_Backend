"""
Colecciones endpoints (CU15 / v5 sección 14).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.coleccion import Coleccion
from app.models.producto import Producto
from app.schemas.coleccion import ColeccionCreate, ColeccionUpdate, ColeccionResponse
from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.bitacora_service import BitacoraService

router = APIRouter(prefix="/colecciones", tags=["Colecciones"])


@router.get("", response_model=list[ColeccionResponse], summary="Listar colecciones")
async def list_colecciones(
    current_user: User = Depends(require_permission("colecciones.ver")),
    db: Session = Depends(get_db),
):
    """Listar todas las colecciones de prendas."""
    return db.query(Coleccion).order_by(Coleccion.nombre).all()


@router.post("", response_model=ColeccionResponse, status_code=status.HTTP_201_CREATED, summary="Crear colección")
async def create_coleccion(
    payload: ColeccionCreate,
    current_user: User = Depends(require_permission("colecciones.crear")),
    db: Session = Depends(get_db),
):
    """Crear una nueva colección con nombre único."""
    existing = db.query(Coleccion).filter(Coleccion.nombre.ilike(payload.nombre.strip())).first()
    if existing:
        raise BadRequestException(f"Ya existe una colección con el nombre '{payload.nombre.strip()}'.")

    item = Coleccion(
        nombre=payload.nombre.strip(),
        descripcion=payload.descripcion.strip() if payload.descripcion else None,
        active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Creó la colección '{item.nombre}' (ID: {item.id})",
        module="colecciones",
    )
    return item


@router.get("/{coleccion_id}", response_model=ColeccionResponse, summary="Obtener detalle de colección")
async def get_coleccion(
    coleccion_id: int,
    current_user: User = Depends(require_permission("colecciones.ver")),
    db: Session = Depends(get_db),
):
    """Obtener una colección por ID."""
    item = db.query(Coleccion).filter(Coleccion.id == coleccion_id).first()
    if not item:
        raise NotFoundException(f"Colección con ID {coleccion_id} no encontrada.")
    return item


@router.put("/{coleccion_id}", response_model=ColeccionResponse, summary="Editar colección")
async def update_coleccion(
    coleccion_id: int,
    payload: ColeccionUpdate,
    current_user: User = Depends(require_permission("colecciones.editar")),
    db: Session = Depends(get_db),
):
    """Editar información de una colección."""
    item = db.query(Coleccion).filter(Coleccion.id == coleccion_id).first()
    if not item:
        raise NotFoundException(f"Colección con ID {coleccion_id} no encontrada.")

    if payload.nombre and payload.nombre.strip() != item.nombre:
        existing = db.query(Coleccion).filter(
            Coleccion.nombre.ilike(payload.nombre.strip()),
            Coleccion.id != coleccion_id,
        ).first()
        if existing:
            raise BadRequestException(f"Ya existe otra colección con el nombre '{payload.nombre.strip()}'.")
        item.nombre = payload.nombre.strip()

    if payload.descripcion is not None:
        item.descripcion = payload.descripcion.strip() if payload.descripcion else None
    if payload.active is not None:
        item.active = payload.active

    db.commit()
    db.refresh(item)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Actualizó la colección '{item.nombre}' (ID: {item.id})",
        module="colecciones",
    )
    return item


@router.delete("/{coleccion_id}", summary="Eliminar colección")
async def delete_coleccion(
    coleccion_id: int,
    current_user: User = Depends(require_permission("colecciones.eliminar")),
    db: Session = Depends(get_db),
):
    """Eliminar colección validando que no tenga productos asociados."""
    item = db.query(Coleccion).filter(Coleccion.id == coleccion_id).first()
    if not item:
        raise NotFoundException(f"Colección con ID {coleccion_id} no encontrada.")

    related_prods = db.query(Producto).filter(Producto.coleccion_id == coleccion_id).count()
    if related_prods > 0:
        raise BadRequestException(f"No se puede eliminar la colección '{item.nombre}' porque tiene {related_prods} producto(s) asociado(s).")

    db.delete(item)
    db.commit()

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Eliminó la colección '{item.nombre}' (ID: {coleccion_id})",
        module="colecciones",
    )
    return {"message": f"Colección '{item.nombre}' eliminada exitosamente."}
