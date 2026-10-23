"""
Endpoints de Notificaciones y Suscripciones (v6 Punto 5).
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.proximamente import Proximamente
from app.models.stock_inventario import StockInventario
from app.services.notificacion_service import NotificacionService
from app.services.tenant_scope import scope_by_sucursal
from app.api.deps import get_current_user
from app.services.push_notification_service import PushNotificationService

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])


class SuscribirProximamenteRequest(BaseModel):
    proximamente_id: int


class SuscribirStockRequest(BaseModel):
    stock_inventario_id: int


class PushDeviceRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    platform: Literal["android", "ios", "web"] = "android"
    device_id: str | None = Field(default=None, max_length=160)


class PushDeviceDeleteRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)


@router.post("/dispositivos", summary="Registrar instalación para notificaciones push")
async def register_push_device(
    payload: PushDeviceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.empresa_id is None:
        raise HTTPException(status_code=400, detail="Selecciona una empresa antes de registrar el dispositivo")
    device = PushNotificationService.register_device(
        db,
        user_id=current_user.id,
        empresa_id=current_user.empresa_id,
        token=payload.token,
        platform=payload.platform,
        device_id=payload.device_id,
    )
    return {"status": "registered", "device_id": device.id}


@router.delete("/dispositivos", summary="Desactivar instalación de notificaciones push")
async def unregister_push_device(
    payload: PushDeviceDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    PushNotificationService.unregister_device(db, user_id=current_user.id, token=payload.token)
    return {"status": "unregistered"}


@router.get("/mis-notificaciones", summary="Listar notificaciones del usuario actual")
async def get_mis_notificaciones(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NotificacionService(db)
    items = service.listar_notificaciones_usuario(user_id=current_user.id, empresa_id=current_user.empresa_id, limit=limit, offset=offset)
    unread_count = service.contar_no_leidas(user_id=current_user.id, empresa_id=current_user.empresa_id)
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
    count = service.contar_no_leidas(user_id=current_user.id, empresa_id=current_user.empresa_id)
    return {"count": count}


@router.put("/{notificacion_id}/leer", summary="Marcar una notificación como leída")
async def marcar_notificacion_leida(
    notificacion_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NotificacionService(db)
    success = service.marcar_como_leida(notificacion_id=notificacion_id, user_id=current_user.id, empresa_id=current_user.empresa_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return {"status": "ok", "mensaje": "Notificación marcada como leída"}


@router.put("/leer-todas", summary="Marcar todas las notificaciones como leídas")
async def marcar_todas_leidas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NotificacionService(db)
    count = service.marcar_todas_leidas(user_id=current_user.id, empresa_id=current_user.empresa_id)
    return {"status": "ok", "actualizadas": count}


@router.post("/suscribir-proximamente", summary="Suscribirse a alertas de artículo de Próximamente")
async def suscribir_proximamente(
    payload: SuscribirProximamenteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Proximamente).filter(
        Proximamente.id == payload.proximamente_id,
        Proximamente.empresa_id == current_user.empresa_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Artículo próximo no encontrado")
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
    stock = scope_by_sucursal(
        db.query(StockInventario).filter(StockInventario.id == payload.stock_inventario_id),
        db,
        current_user,
        StockInventario.sucursal_id,
    ).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Existencia no encontrada")
    service = NotificacionService(db)
    resultado = service.suscribir_stock(
        user_id=current_user.id, stock_inventario_id=payload.stock_inventario_id
    )
    return resultado
