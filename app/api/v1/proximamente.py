"""
Próximamente endpoints (v5 sección 11).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.proximamente import Proximamente
from app.schemas.proximamente import ProximamenteCreate, ProximamenteUpdate, ProximamenteResponse
from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundException
from app.services.bitacora_service import BitacoraService

router = APIRouter(prefix="/proximamente", tags=["Próximamente"])


def _serialize_proximamente(item: Proximamente) -> dict:
    return {
        "id": item.id,
        "nombre": item.nombre,
        "descripcion": item.descripcion,
        "foto": item.foto,
        "fecha_estimada_llegada": item.fecha_estimada_llegada,
        "proveedor_codigo": item.proveedor_codigo,
        "categoria_id": item.categoria_id,
        "temporada_id": item.temporada_id,
        "coleccion_id": item.coleccion_id,
        "active": item.active,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "categoria_nombre": item.categoria.nombre if item.categoria else None,
        "temporada_nombre": item.temporada.nombre if item.temporada else None,
        "coleccion_nombre": item.coleccion.nombre if item.coleccion else None,
        "proveedor_nombre": f"{item.proveedor.nombre} {item.proveedor.apellido}" if item.proveedor else None,
    }


@router.get("", response_model=list[ProximamenteResponse], summary="Listar prendas próximas")
async def list_proximamente(
    db: Session = Depends(get_db),
):
    """Listar todas las prendas próximas activas para catálogo y administración."""
    items = db.query(Proximamente).order_by(Proximamente.fecha_estimada_llegada.asc().nulls_last()).all()
    return [_serialize_proximamente(i) for i in items]


@router.post("", response_model=ProximamenteResponse, status_code=status.HTTP_201_CREATED, summary="Crear prenda próxima")
async def create_proximamente(
    payload: ProximamenteCreate,
    current_user: User = Depends(require_permission("proximamente.crear")),
    db: Session = Depends(get_db),
):
    """Registrar una nueva prenda de próximo lanzamiento."""
    item = Proximamente(
        nombre=payload.nombre.strip(),
        descripcion=payload.descripcion.strip() if payload.descripcion else None,
        foto=payload.foto.strip() if payload.foto else None,
        fecha_estimada_llegada=payload.fecha_estimada_llegada,
        proveedor_codigo=payload.proveedor_codigo,
        categoria_id=payload.categoria_id,
        temporada_id=payload.temporada_id,
        coleccion_id=payload.coleccion_id,
        active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Registró la prenda próxima '{item.nombre}' (ID: {item.id})",
        module="proximamente",
    )
    return _serialize_proximamente(item)


@router.get("/{item_id}", response_model=ProximamenteResponse, summary="Obtener prenda próxima")
async def get_proximamente(
    item_id: int,
    db: Session = Depends(get_db),
):
    """Obtener detalle de una prenda próxima."""
    item = db.query(Proximamente).filter(Proximamente.id == item_id).first()
    if not item:
        raise NotFoundException(f"Prenda próxima con ID {item_id} no encontrada.")
    return _serialize_proximamente(item)


@router.put("/{item_id}", response_model=ProximamenteResponse, summary="Editar prenda próxima")
async def update_proximamente(
    item_id: int,
    payload: ProximamenteUpdate,
    current_user: User = Depends(require_permission("proximamente.editar")),
    db: Session = Depends(get_db),
):
    """Editar información de una prenda de próximo lanzamiento."""
    item = db.query(Proximamente).filter(Proximamente.id == item_id).first()
    if not item:
        raise NotFoundException(f"Prenda próxima con ID {item_id} no encontrada.")

    if payload.nombre is not None:
        item.nombre = payload.nombre.strip()
    if payload.descripcion is not None:
        item.descripcion = payload.descripcion.strip() if payload.descripcion else None
    if payload.foto is not None:
        item.foto = payload.foto.strip() if payload.foto else None
    if payload.fecha_estimada_llegada is not None:
        item.fecha_estimada_llegada = payload.fecha_estimada_llegada
    if payload.proveedor_codigo is not None:
        item.proveedor_codigo = payload.proveedor_codigo
    if payload.categoria_id is not None:
        item.categoria_id = payload.categoria_id
    if payload.temporada_id is not None:
        item.temporada_id = payload.temporada_id
    if payload.coleccion_id is not None:
        item.coleccion_id = payload.coleccion_id
    if payload.active is not None:
        item.active = payload.active

    db.commit()
    db.refresh(item)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Actualizó la prenda próxima '{item.nombre}' (ID: {item.id})",
        module="proximamente",
    )
    return _serialize_proximamente(item)


@router.delete("/{item_id}", summary="Eliminar prenda próxima")
async def delete_proximamente(
    item_id: int,
    current_user: User = Depends(require_permission("proximamente.eliminar")),
    db: Session = Depends(get_db),
):
    """Eliminar prenda próxima."""
    item = db.query(Proximamente).filter(Proximamente.id == item_id).first()
    if not item:
        raise NotFoundException(f"Prenda próxima con ID {item_id} no encontrada.")

    db.delete(item)
    db.commit()

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Eliminó la prenda próxima '{item.nombre}' (ID: {item_id})",
        module="proximamente",
    )
    return {"message": f"Prenda próxima '{item.nombre}' eliminada exitosamente."}
