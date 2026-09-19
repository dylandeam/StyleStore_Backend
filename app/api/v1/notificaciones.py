"""
Endpoints de Notificaciones y Suscripciones (v6 Punto 5).
"""
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.notificacion_service import NotificacionService
from app.api.deps import get_current_user

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])


class SuscribirProximamenteRequest(BaseModel):
    proximamente_id: int


class SuscribirStockRequest(BaseModel):
    stock_inventario_id: int


@router.get("/mis-notificaciones", summary="Listar notificaciones del usuario actual")
async def get_mis_notificaciones(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NotificacionService(db)
    items = service.listar_notificaciones_usuario(user_id=current_user.id, limit=limit, offset=offset)
    unread_count = service.contar_no_leidas(user_id=current_user.id)
    return {
        "items": items,
        "total_no_leidas": unread_count,
    }


@router.get("/no-leidas-count", summary="Obtener contador de notificaciones no leídas")
async def get_no_leidas_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NotificacionService(db)
    count = service.contar_no_leidas(user_id=current_user.id)
    return {"count": count}


@router.put("/{notificacion_id}/leer", summary="Marcar una notificación como leída")
async def marcar_notificacion_leida(
    notificacion_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NotificacionService(db)
    success = service.marcar_como_leida(notificacion_id=notificacion_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return {"status": "ok", "mensaje": "Notificación marcada como leída"}


@router.put("/leer-todas", summary="Marcar todas las notificaciones como leídas")
async def marcar_todas_leidas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NotificacionService(db)
    count = service.marcar_todas_leidas(user_id=current_user.id)
    return {"status": "ok", "actualizadas": count}


@router.post("/suscribir-proximamente", summary="Suscribirse a alertas de artículo de Próximamente")
async def suscribir_proximamente(
    payload: SuscribirProximamenteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NotificacionService(db)
    resultado = service.suscribir_proximamente(
        user_id=current_user.id, proximamente_id=payload.proximamente_id
    )
    return resultado


@router.post("/suscribir-stock", summary="Suscribirse a alertas de reposición de stock")
async def suscribir_stock(
    payload: SuscribirStockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NotificacionService(db)
    resultado = service.suscribir_stock(
        user_id=current_user.id, stock_inventario_id=payload.stock_inventario_id
    )
    return resultado
