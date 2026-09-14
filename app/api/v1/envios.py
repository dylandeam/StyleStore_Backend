"""
Envíos endpoints (v5 sección 20 y 24).
Cálculo automático de tarifas escalonadas y seguimiento de despachos a domicilio.
"""
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.orden_venta import OrdenVenta
from app.models.envio import Envio
from app.schemas.pago_envio import (
    EnvioCotizacionRequest,
    EnvioCreateRequest,
    EnvioUpdateRequest,
    EnvioResponse,
)
from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.bitacora_service import BitacoraService

router = APIRouter(prefix="/envios", tags=["Envíos"])


def _calcular_tarifa_escalonada(distancia_km: float) -> Decimal:
    """Tabla de tarifas de referencia escalonadas v5 (sección 20):
    0-3 km: Bs 8
    3-6 km: Bs 12
    6-10 km: Bs 18
    >10 km: Bs 25
    """
    if distancia_km <= 3.0:
        return Decimal("8.00")
    elif distancia_km <= 6.0:
        return Decimal("12.00")
    elif distancia_km <= 10.0:
        return Decimal("18.00")
    else:
        return Decimal("25.00")


def _serialize_envio(e: Envio) -> dict:
    cli_name = None
    if e.orden_venta and e.orden_venta.cliente and e.orden_venta.cliente.user:
        u = e.orden_venta.cliente.user
        cli_name = f"{u.name} {u.apellido or ''}".strip()

    return {
        "id": e.id,
        "orden_venta_id": e.orden_venta_id,
        "direccion": e.direccion,
        "ciudad": e.ciudad,
        "referencia": e.referencia,
        "costo": e.costo,
        "estado": e.estado,
        "fecha": e.fecha,
        "created_at": e.created_at,
        "cliente_nombre": cli_name,
    }


@router.post("/cotizar", summary="Cotizar tarifa escalonada de envío")
async def cotizar_envio(payload: EnvioCotizacionRequest):
    """Calcula el costo del envío según la distancia estimada en km."""
    costo = _calcular_tarifa_escalonada(payload.distancia_km)
    return {
        "distancia_km": payload.distancia_km,
        "costo": costo,
        "moneda": "BOB",
    }


@router.post("", response_model=EnvioResponse, status_code=status.HTTP_201_CREATED, summary="Registrar envío")
async def create_envio(
    payload: EnvioCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea el registro de envío asociado a una orden de venta."""
    orden = db.query(OrdenVenta).filter(OrdenVenta.id == payload.orden_venta_id).first()
    if not orden:
        raise NotFoundException(f"Orden de venta con ID {payload.orden_venta_id} no encontrada.")

    # Calcular costo según distancia si se provee, o usar tabla por defecto
    if payload.costo is not None:
        costo = payload.costo
    elif payload.distancia_km is not None:
        costo = _calcular_tarifa_escalonada(payload.distancia_km)
    else:
        costo = Decimal("12.00")  # Valor intermedio de referencia

    envio = Envio(
        orden_venta_id=orden.id,
        direccion=payload.direccion.strip(),
        ciudad=payload.ciudad.strip(),
        referencia=payload.referencia.strip() if payload.referencia else None,
        costo=costo,
        estado="pendiente",
        fecha=datetime.now().date(),
    )
    db.add(envio)
    db.commit()
    db.refresh(envio)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Registró envío #{envio.id} a {envio.ciudad} para Orden #{orden.id} (Costo: Bs {envio.costo})",
        module="envios",
    )

    return _serialize_envio(envio)


@router.patch("/{envio_id}/completar", response_model=EnvioResponse, summary="Marcar envío como completado por el cliente")
async def complete_envio(
    envio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Actualiza el estado del envío a 'completado' cuando el cliente confirma recepción."""
    envio = db.query(Envio).filter(Envio.id == envio_id).first()
    if not envio:
        raise NotFoundException(f"Envío con ID {envio_id} no encontrado.")

    envio.estado = "completado"
    if envio.orden_venta:
        envio.orden_venta.estado = "entregada"

    db.commit()
    db.refresh(envio)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Confirmó entrega del pedido en envío #{envio.id}",
        module="envios",
    )
    return _serialize_envio(envio)


@router.get("", response_model=list[EnvioResponse], summary="Listar envíos (Administración)")
async def list_envios(
    current_user: User = Depends(require_permission("envios.ver")),
    db: Session = Depends(get_db),
):
    """Listado administrativo de despachos y envíos."""
    envios = db.query(Envio).order_by(Envio.created_at.desc()).all()
    return [_serialize_envio(e) for e in envios]


@router.put("/{envio_id}", response_model=EnvioResponse, summary="Editar envío")
async def update_envio(
    envio_id: int,
    payload: EnvioUpdateRequest,
    current_user: User = Depends(require_permission("envios.editar")),
    db: Session = Depends(get_db),
):
    """Editar detalles de un envío."""
    envio = db.query(Envio).filter(Envio.id == envio_id).first()
    if not envio:
        raise NotFoundException(f"Envío con ID {envio_id} no encontrado.")

    if payload.direccion is not None:
        envio.direccion = payload.direccion.strip()
    if payload.ciudad is not None:
        envio.ciudad = payload.ciudad.strip()
    if payload.referencia is not None:
        envio.referencia = payload.referencia.strip() if payload.referencia else None
    if payload.costo is not None:
        envio.costo = payload.costo
    if payload.estado is not None:
        envio.estado = payload.estado

    db.commit()
    db.refresh(envio)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Actualizó datos del envío #{envio.id} ({envio.estado})",
        module="envios",
    )
    return _serialize_envio(envio)


@router.delete("/{envio_id}", summary="Eliminar envío")
async def delete_envio(
    envio_id: int,
    current_user: User = Depends(require_permission("envios.eliminar")),
    db: Session = Depends(get_db),
):
    """Eliminar un envío."""
    envio = db.query(Envio).filter(Envio.id == envio_id).first()
    if not envio:
        raise NotFoundException(f"Envío con ID {envio_id} no encontrado.")

    db.delete(envio)
    db.commit()

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Eliminó el envío #{envio_id}",
        module="envios",
    )
    return {"message": f"Envío #{envio_id} eliminado exitosamente."}
