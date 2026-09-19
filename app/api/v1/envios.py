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
from app.models.cliente import Cliente
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
        "ubicacion_url": getattr(e, "ubicacion_url", None),
        "costo": e.costo,
        "estado": e.estado,
        "fecha": e.fecha,
        "yango_tracking_code": e.yango_tracking_code,
        "yango_tracking_url": e.yango_tracking_url,
        "delivery_conductor": e.delivery_conductor,
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

    dir_val = payload.direccion.strip() if payload.direccion else ""
    ub_url = payload.ubicacion_url.strip() if payload.ubicacion_url else None
    if not dir_val and ub_url:
        dir_val = "Ubicación GPS (Ver enlace)"

    envio = Envio(
        orden_venta_id=orden.id,
        direccion=dir_val,
        ciudad=payload.ciudad.strip() if payload.ciudad else "Santa Cruz",
        referencia=payload.referencia.strip() if payload.referencia else None,
        ubicacion_url=ub_url,
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


from app.schemas.pago_envio import EnvioYangoUpdateRequest


@router.patch("/{envio_id}/yango", response_model=EnvioResponse, summary="Asignar o actualizar tracking de Yango Delivery")
async def update_yango_tracking(
    envio_id: int,
    payload: EnvioYangoUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    El encargado ingresa a mano el código de Yango Delivery, URL de seguimiento y conductor.
    Actualiza el estado a 'en camino' si no se especifica otro.
    """
    envio = db.query(Envio).filter(Envio.id == envio_id).first()
    if not envio:
        raise NotFoundException(f"Envío con ID {envio_id} no encontrado.")

    if payload.yango_tracking_code is not None:
        envio.yango_tracking_code = payload.yango_tracking_code.strip()
    if payload.yango_tracking_url is not None:
        envio.yango_tracking_url = payload.yango_tracking_url.strip()
    if payload.delivery_conductor is not None:
        envio.delivery_conductor = payload.delivery_conductor.strip()
    if payload.estado is not None:
        envio.estado = payload.estado
    else:
        envio.estado = "en camino"

    if envio.orden_venta and envio.estado == "en camino":
        envio.orden_venta.estado = "en camino"

    db.commit()
    db.refresh(envio)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Actualizó despacho Yango para Envío #{envio.id} (Código: {envio.yango_tracking_code}, Repartidor: {envio.delivery_conductor})",
        module="envios",
    )
    return _serialize_envio(envio)


@router.get("/orden/{orden_id}", response_model=EnvioResponse, summary="Consultar envío por Orden de Venta")
async def get_envio_by_orden(
    orden_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permite al cliente o encargado ver el estado y tracking en vivo del envío de su orden."""
    envio = db.query(Envio).filter(Envio.orden_venta_id == orden_id).first()
    if not envio:
        raise NotFoundException(f"No hay despacho registrado para la orden #{orden_id}.")
    return _serialize_envio(envio)


@router.get("", response_model=list[EnvioResponse], summary="Listar envíos (Administración y Clientes)")
async def list_envios(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Listado de envíos. Si es cliente retorna sus envíos, si es staff retorna todos."""
    if current_user.role == "cliente":
        cliente = db.query(Cliente).filter(Cliente.user_id == current_user.id).first()
        if not cliente:
            return []
        envios = (
            db.query(Envio)
            .join(OrdenVenta, Envio.orden_venta_id == OrdenVenta.id)
            .filter(OrdenVenta.codigo_cliente == cliente.codigo)
            .order_by(Envio.created_at.desc())
            .all()
        )
        return [_serialize_envio(e) for e in envios]

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
    if payload.ubicacion_url is not None:
        envio.ubicacion_url = payload.ubicacion_url.strip() if payload.ubicacion_url else None
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
