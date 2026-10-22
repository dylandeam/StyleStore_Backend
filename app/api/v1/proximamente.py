"""
Próximamente endpoints (v5 sección 11).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.proximamente import Proximamente
from app.models.empresa import Empresa
from app.models.proveedor import Proveedor
from app.models.categoria import Categoria
from app.models.temporada import Temporada
from app.models.coleccion import Coleccion
from app.schemas.proximamente import ProximamenteCreate, ProximamenteUpdate, ProximamenteResponse
from app.api.deps import get_optional_current_user, require_permission
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.services.bitacora_service import BitacoraService
from app.services.notificacion_service import NotificacionService

router = APIRouter(prefix="/proximamente", tags=["Próximamente"])


def _serialize_proximamente(item: Proximamente) -> dict:
    return {
        "id": item.id,
        "empresa_id": item.empresa_id,
        "empresa_nombre": item.empresa.nombre if item.empresa else None,
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


def _tenant_mutacion(current_user: User) -> int:
    if current_user.is_platform_admin:
        raise ForbiddenException("El administrador SaaS supervisa; cada tenant gestiona sus próximos lanzamientos.")
    if not current_user.empresa_id:
        raise BadRequestException("Tu usuario no tiene un tenant activo.")
    return current_user.empresa_id


def _validar_referencias(db: Session, empresa_id: int, payload) -> None:
    referencias = [
        (Proveedor, "codigo", payload.proveedor_codigo, "proveedor"),
        (Categoria, "id", payload.categoria_id, "categoría"),
        (Temporada, "id", payload.temporada_id, "temporada"),
        (Coleccion, "id", payload.coleccion_id, "colección"),
    ]
    for model, key, value, label in referencias:
        if value is None:
            continue
        exists = db.query(model).filter(getattr(model, key) == value, model.empresa_id == empresa_id).first()
        if not exists:
            raise NotFoundException(f"La referencia de {label} no pertenece al tenant activo.")


@router.get("", response_model=list[ProximamenteResponse], summary="Listar prendas próximas")
async def list_proximamente(
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Listar todas las prendas próximas activas para catálogo y administración."""
    query = db.query(Proximamente)
    if current_user and current_user.is_platform_admin:
        pass
    elif current_user and current_user.empresa_id:
        query = query.filter(Proximamente.empresa_id == current_user.empresa_id)
    else:
        default = db.query(Empresa).filter(Empresa.codigo == "stylestore").first()
        query = query.filter(Proximamente.empresa_id == default.id, Proximamente.active.is_(True)) if default else query.filter(False)
    items = query.order_by(Proximamente.fecha_estimada_llegada.asc().nulls_last()).all()
    return [_serialize_proximamente(i) for i in items]


@router.post("", response_model=ProximamenteResponse, status_code=status.HTTP_201_CREATED, summary="Crear prenda próxima")
async def create_proximamente(
    payload: ProximamenteCreate,
    current_user: User = Depends(require_permission("proximamente.crear")),
    db: Session = Depends(get_db),
):
    """Registrar una nueva prenda de próximo lanzamiento."""
    empresa_id = _tenant_mutacion(current_user)
    _validar_referencias(db, empresa_id, payload)
    item = Proximamente(
        empresa_id=empresa_id,
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
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Obtener detalle de una prenda próxima."""
    query = db.query(Proximamente).filter(Proximamente.id == item_id)
    if not (current_user and current_user.is_platform_admin):
        empresa_id = current_user.empresa_id if current_user else None
        if empresa_id is None:
            default = db.query(Empresa).filter(Empresa.codigo == "stylestore").first()
            empresa_id = default.id if default else None
        query = query.filter(Proximamente.empresa_id == empresa_id)
    item = query.first()
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
    empresa_id = _tenant_mutacion(current_user)
    item = db.query(Proximamente).filter(
        Proximamente.id == item_id, Proximamente.empresa_id == empresa_id
    ).first()
    if not item:
        raise NotFoundException(f"Prenda próxima con ID {item_id} no encontrada.")

    _validar_referencias(db, empresa_id, payload)
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


@router.post("/{item_id}/notificar", summary="Notificar llegada o disponibilidad a clientes suscritos")
async def notificar_proximamente(
    item_id: int,
    current_user: User = Depends(require_permission("proximamente.editar")),
    db: Session = Depends(get_db),
):
    """Notificar disponibilidad del artículo a todos los clientes suscritos."""
    empresa_id = _tenant_mutacion(current_user)
    item = db.query(Proximamente).filter(
        Proximamente.id == item_id, Proximamente.empresa_id == empresa_id
    ).first()
    if not item:
        raise NotFoundException(f"Prenda próxima con ID {item_id} no encontrada.")

    item.active = True
    db.commit()

    service = NotificacionService(db)
    total_notificados = service.notificar_llegada_proximamente(proximamente_id=item.id)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Notificó la llegada de la prenda próxima '{item.nombre}' a {total_notificados} clientes suscritos",
        module="proximamente",
    )
    return {
        "message": f"Se notificó con éxito a {total_notificados} clientes suscritos sobre la llegada de '{item.nombre}'.",
        "total_notificados": total_notificados,
        "item": _serialize_proximamente(item),
    }


@router.delete("/{item_id}", summary="Eliminar prenda próxima")
async def delete_proximamente(
    item_id: int,
    current_user: User = Depends(require_permission("proximamente.eliminar")),
    db: Session = Depends(get_db),
):
    """Eliminar prenda próxima."""
    empresa_id = _tenant_mutacion(current_user)
    item = db.query(Proximamente).filter(
        Proximamente.id == item_id, Proximamente.empresa_id == empresa_id
    ).first()
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
