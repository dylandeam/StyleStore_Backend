"""Calificaciones del servicio y gestión de reclamos poscompra."""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.cliente import Cliente
from app.models.experiencia import CalificacionServicio, Reclamo
from app.models.orden_venta import OrdenVenta
from app.models.sucursal import Sucursal
from app.models.user import User
from app.schemas.experiencia import (
    CalificacionCreate, CalificacionResponse, ReclamoCreate, ReclamoResponse, ReclamoUpdate,
)
from app.services.bitacora_service import BitacoraService
from app.services.notificacion_service import NotificacionService

router = APIRouter(prefix="/experiencia", tags=["Calificaciones y Reclamos"])
LOW_RATING_MAX = 2


def _client_order(db: Session, user: User, order_id: int) -> OrdenVenta:
    cliente = db.query(Cliente).filter(Cliente.user_id == user.id).first()
    order = db.query(OrdenVenta).filter(
        OrdenVenta.id == order_id,
        OrdenVenta.codigo_cliente == (cliente.codigo if cliente else ""),
    ).first()
    if (
        not order
        or user.empresa_id is None
        or not order.sucursal
        or order.sucursal.empresa_id != user.empresa_id
    ):
        raise HTTPException(status_code=404, detail="Compra no encontrada en el tenant activo.")
    return order


def _rating_dict(item: CalificacionServicio) -> dict:
    return {
        "id": item.id, "empresa_id": item.empresa_id,
        "empresa_nombre": item.empresa.nombre if item.empresa else None,
        "user_id": item.user_id,
        "cliente_nombre": f"{item.user.name} {item.user.apellido or ''}".strip() if item.user else None,
        "orden_venta_id": item.orden_venta_id, "sucursal_id": item.sucursal_id,
        "sucursal_nombre": item.sucursal.nombre if item.sucursal else None,
        "puntuacion": item.puntuacion, "comentario": item.comentario,
        "created_at": item.created_at,
        "sugerir_reclamo": item.puntuacion <= LOW_RATING_MAX,
        "mensaje": "Lamentamos que tu experiencia no haya sido satisfactoria. Puedes registrar un reclamo para que podamos ayudarte." if item.puntuacion <= LOW_RATING_MAX else "Gracias por compartir tu experiencia.",
    }


def _claim_dict(item: Reclamo) -> dict:
    return {
        "id": item.id, "empresa_id": item.empresa_id,
        "empresa_nombre": item.empresa.nombre if item.empresa else None,
        "user_id": item.user_id,
        "cliente_nombre": f"{item.user.name} {item.user.apellido or ''}".strip() if item.user else None,
        "orden_venta_id": item.orden_venta_id, "calificacion_id": item.calificacion_id,
        "sucursal_id": item.sucursal_id,
        "sucursal_nombre": item.sucursal.nombre if item.sucursal else None,
        "fecha_incidente": item.fecha_incidente, "motivo": item.motivo,
        "descripcion": item.descripcion, "estado": item.estado,
        "respuesta": item.respuesta, "created_at": item.created_at, "updated_at": item.updated_at,
    }


@router.get("/resumen", summary="Resumen público de calificaciones del tenant")
async def rating_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.empresa_id is None:
        return {"promedio": 0, "total": 0, "distribucion": {str(i): 0 for i in range(1, 6)}}
    rows = db.query(CalificacionServicio.puntuacion, func.count(CalificacionServicio.id)).filter(
        CalificacionServicio.empresa_id == current_user.empresa_id
    ).group_by(CalificacionServicio.puntuacion).all()
    distribution = {str(i): 0 for i in range(1, 6)}
    for score, count in rows:
        distribution[str(score)] = count
    total = sum(distribution.values())
    average = sum(int(score) * count for score, count in distribution.items()) / total if total else 0
    return {"promedio": round(average, 2), "total": total, "distribucion": distribution}


@router.get("/calificaciones", response_model=list[CalificacionResponse])
async def list_ratings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(CalificacionServicio)
    if current_user.role == "cliente":
        query = query.filter(CalificacionServicio.user_id == current_user.id, CalificacionServicio.empresa_id == current_user.empresa_id)
    elif not current_user.is_platform_admin:
        query = query.filter(CalificacionServicio.empresa_id == current_user.empresa_id)
    return [_rating_dict(item) for item in query.order_by(CalificacionServicio.created_at.desc()).all()]


@router.post("/calificaciones", response_model=CalificacionResponse, status_code=status.HTTP_201_CREATED)
async def create_rating(payload: CalificacionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "cliente":
        raise HTTPException(status_code=403, detail="Solo los clientes pueden calificar el servicio.")
    order = _client_order(db, current_user, payload.orden_venta_id)
    if order.estado not in {"pagada", "entregada", "completada"}:
        raise HTTPException(status_code=400, detail="La compra debe estar pagada o entregada antes de calificar.")
    item = db.query(CalificacionServicio).filter(
        CalificacionServicio.user_id == current_user.id,
        CalificacionServicio.orden_venta_id == order.id,
    ).first()
    if item:
        item.puntuacion = payload.puntuacion
        item.comentario = payload.comentario.strip() if payload.comentario else None
    else:
        item = CalificacionServicio(
            empresa_id=current_user.empresa_id, user_id=current_user.id,
            orden_venta_id=order.id, sucursal_id=order.sucursal_id,
            puntuacion=payload.puntuacion,
            comentario=payload.comentario.strip() if payload.comentario else None,
        )
        db.add(item)
    db.commit()
    db.refresh(item)
    return _rating_dict(item)


@router.get("/reclamos", response_model=list[ReclamoResponse])
async def list_claims(
    estado: str | None = Query(None),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    query = db.query(Reclamo)
    if current_user.role == "cliente":
        query = query.filter(Reclamo.user_id == current_user.id, Reclamo.empresa_id == current_user.empresa_id)
    elif not current_user.is_platform_admin:
        query = query.filter(Reclamo.empresa_id == current_user.empresa_id)
    if estado:
        query = query.filter(Reclamo.estado == estado)
    return [_claim_dict(item) for item in query.order_by(Reclamo.created_at.desc()).all()]


@router.post("/reclamos", response_model=ReclamoResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(payload: ReclamoCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "cliente" or current_user.empresa_id is None:
        raise HTTPException(status_code=403, detail="Solo los clientes pueden registrar reclamos.")
    if payload.fecha_incidente > date.today():
        raise HTTPException(status_code=400, detail="La fecha del incidente no puede estar en el futuro.")
    branch = db.query(Sucursal).filter(
        Sucursal.id == payload.sucursal_id, Sucursal.empresa_id == current_user.empresa_id
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada en el tenant activo.")
    order = _client_order(db, current_user, payload.orden_venta_id) if payload.orden_venta_id else None
    rating = None
    if payload.calificacion_id:
        rating = db.query(CalificacionServicio).filter(
            CalificacionServicio.id == payload.calificacion_id,
            CalificacionServicio.user_id == current_user.id,
            CalificacionServicio.empresa_id == current_user.empresa_id,
        ).first()
        if not rating:
            raise HTTPException(status_code=404, detail="Calificación no encontrada.")
    item = Reclamo(
        empresa_id=current_user.empresa_id, user_id=current_user.id,
        orden_venta_id=order.id if order else None,
        calificacion_id=rating.id if rating else None,
        sucursal_id=branch.id, fecha_incidente=payload.fecha_incidente,
        motivo=payload.motivo.strip().lower(), descripcion=payload.descripcion.strip(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    BitacoraService.registrar(db, current_user, f"Registró reclamo #{item.id} por {item.motivo}", "reclamos")
    return _claim_dict(item)


@router.patch("/reclamos/{reclamo_id}", response_model=ReclamoResponse)
async def update_claim(
    reclamo_id: int, payload: ReclamoUpdate,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    if current_user.is_platform_admin:
        raise HTTPException(status_code=403, detail="El administrador SaaS supervisa reclamos, pero la respuesta corresponde al tenant.")
    if current_user.role not in {"administrador", "encargado_sucursal"}:
        raise HTTPException(status_code=403, detail="Solo el administrador o encargado del tenant puede gestionar reclamos.")
    query = db.query(Reclamo).filter(Reclamo.id == reclamo_id)
    if not current_user.is_platform_admin:
        query = query.filter(Reclamo.empresa_id == current_user.empresa_id)
    item = query.first()
    if not item:
        raise HTTPException(status_code=404, detail="Reclamo no encontrado.")
    item.estado = payload.estado
    item.respuesta = payload.respuesta.strip() if payload.respuesta else None
    if payload.estado in {"resuelto", "rechazado"}:
        item.resuelto_por_id = current_user.id
        item.resuelto_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    NotificacionService(db).crear_notificacion(
        user_id=item.user_id, tipo="reclamo_actualizado",
        titulo=f"Actualización de tu reclamo #{item.id}",
        mensaje=f"Tu reclamo ahora está {item.estado.replace('_', ' ')}." + (f" Respuesta: {item.respuesta}" if item.respuesta else ""),
        url_accion="/cuenta/experiencia?tab=reclamos", enviar_email=True,
        empresa_id=item.empresa_id,
    )
    BitacoraService.registrar(db, current_user, f"Actualizó reclamo #{item.id} a {item.estado}", "reclamos")
    return _claim_dict(item)
