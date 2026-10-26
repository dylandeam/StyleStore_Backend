"""
Endpoints de Notificaciones y Suscripciones (v6 Punto 5).
"""
from datetime import datetime
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
from app.models.empresa import Empresa
from app.models.notificacion import CampanaNotificacion
from app.services.campana_notificacion_service import CampanaNotificacionService, as_utc, utcnow

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


class CampanaRequest(BaseModel):
    titulo: str = Field(min_length=3, max_length=200)
    mensaje: str = Field(min_length=3, max_length=2000)
    url_accion: str | None = Field(default=None, max_length=300)
    audiencia: Literal[
        "todos", "clientes", "empleados", "administradores", "usuarios_seleccionados", "admins_tenant"
    ]
    target_user_ids: list[int] = Field(default_factory=list, max_length=500)
    target_empresa_ids: list[int] = Field(default_factory=list, max_length=500)
    programada_para: datetime | None = None
    recurrencia_dias: int | None = Field(default=None, ge=1, le=365)
    enviar_email: bool = False


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


@router.post("/prueba-push", summary="Enviar una notificación push de prueba al usuario actual")
async def test_push_notification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.empresa_id is None:
        raise HTTPException(status_code=400, detail="Selecciona una empresa antes de probar notificaciones")
    sent = PushNotificationService.send_to_user(
        db,
        user_id=current_user.id,
        empresa_id=current_user.empresa_id,
        title="StyleStore está conectado",
        body="Las notificaciones push funcionan correctamente en este dispositivo.",
        data={"type": "push_test", "route": "/dashboard"},
    )
    return {
        "status": "sent" if sent else "no_devices",
        "sent": sent,
        "message": (
            "Notificación enviada."
            if sent
            else "No hay un dispositivo push activo para este usuario y empresa."
        ),
    }


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


def _require_campaign_admin(user: User) -> None:
    if not user.is_platform_admin and user.role != "administrador":
        raise HTTPException(status_code=403, detail="Solo un administrador puede gestionar campañas")


@router.get("/campanas/destinatarios", summary="Destinatarios disponibles para campañas")
async def get_campaign_targets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_campaign_admin(current_user)
    if current_user.is_platform_admin:
        companies = db.query(Empresa).order_by(Empresa.nombre).all()
        return {
            "modo": "saas",
            "empresas": [
                {"id": company.id, "nombre": company.nombre, "active": company.active}
                for company in companies
            ],
            "usuarios": [],
        }
    if current_user.empresa_id is None:
        raise HTTPException(status_code=400, detail="Selecciona una empresa")
    users = CampanaNotificacionService(db)._tenant_users(current_user.empresa_id).order_by(User.name).all()
    return {
        "modo": "tenant",
        "empresas": [],
        "usuarios": [
            {"id": user.id, "nombre": f"{user.name} {user.apellido or ''}".strip(), "email": user.email, "role": user.role}
            for user in users
        ],
    }


@router.get("/campanas", summary="Listar campañas propias")
async def list_campaigns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_campaign_admin(current_user)
    query = db.query(CampanaNotificacion)
    query = query.filter(
        CampanaNotificacion.empresa_id.is_(None)
        if current_user.is_platform_admin
        else CampanaNotificacion.empresa_id == current_user.empresa_id
    )
    return [
        CampanaNotificacionService.serialize(item)
        for item in query.order_by(CampanaNotificacion.created_at.desc()).limit(100).all()
    ]


@router.post("/campanas", summary="Enviar o programar una campaña")
async def create_campaign(
    payload: CampanaRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_campaign_admin(current_user)
    if current_user.is_platform_admin:
        if payload.audiencia != "admins_tenant":
            raise HTTPException(
                status_code=400,
                detail="El administrador SaaS sólo puede notificar a administradores de tenants",
            )
        valid_company_ids = {row[0] for row in db.query(Empresa.id).all()}
        if any(item not in valid_company_ids for item in payload.target_empresa_ids):
            raise HTTPException(status_code=400, detail="Uno de los tenants seleccionados no existe")
        empresa_id = None
    else:
        if current_user.empresa_id is None:
            raise HTTPException(status_code=400, detail="Selecciona una empresa")
        if payload.audiencia == "admins_tenant":
            raise HTTPException(status_code=400, detail="Audiencia no válida para un tenant")
        if payload.audiencia == "usuarios_seleccionados" and not payload.target_user_ids:
            raise HTTPException(status_code=400, detail="Selecciona al menos un usuario")
        allowed_ids = {
            user.id
            for user in CampanaNotificacionService(db)._tenant_users(current_user.empresa_id).all()
        }
        if any(item not in allowed_ids for item in payload.target_user_ids):
            raise HTTPException(status_code=403, detail="Hay usuarios fuera del tenant activo")
        empresa_id = current_user.empresa_id

    scheduled = as_utc(payload.programada_para) if payload.programada_para else utcnow()
    campaign = CampanaNotificacion(
        empresa_id=empresa_id,
        created_by_id=current_user.id,
        titulo=payload.titulo.strip(),
        mensaje=payload.mensaje.strip(),
        url_accion=payload.url_accion.strip() if payload.url_accion else None,
        audiencia=payload.audiencia,
        target_user_ids=payload.target_user_ids,
        target_empresa_ids=payload.target_empresa_ids,
        enviar_email=payload.enviar_email,
        recurrencia_dias=payload.recurrencia_dias,
        proxima_ejecucion=scheduled,
        estado="programada",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    if scheduled <= utcnow():
        campaign = CampanaNotificacionService(db).dispatch(campaign)
    return CampanaNotificacionService.serialize(campaign)


@router.post("/campanas/{campana_id}/cancelar", summary="Cancelar una campaña programada")
async def cancel_campaign(
    campana_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_campaign_admin(current_user)
    campaign = db.get(CampanaNotificacion, campana_id)
    expected_empresa = None if current_user.is_platform_admin else current_user.empresa_id
    if not campaign or campaign.empresa_id != expected_empresa:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    if campaign.estado in {"completada", "cancelada"}:
        raise HTTPException(status_code=400, detail="La campaña ya no se puede cancelar")
    campaign.estado = "cancelada"
    db.commit()
    return CampanaNotificacionService.serialize(campaign)


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
