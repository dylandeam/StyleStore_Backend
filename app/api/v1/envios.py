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

    repartidor_nombre = None
    if e.repartidor:
        repartidor_nombre = f"{e.repartidor.name} {e.repartidor.apellido or ''}".strip()

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
        "tracking_code": e.yango_tracking_code or e.token_seguimiento,
        "tracking_url": e.yango_tracking_url,
        "tracking_activo": getattr(e, "tracking_activo", True),
        "delivery_conductor": e.delivery_conductor,
        "created_at": e.created_at,
        "cliente_nombre": cli_name,
        # Tracking GPS y Repartidor (v7 Punto 7)
        "distancia_km": float(e.distancia_km) if e.distancia_km else None,
        "minutos_estimados": e.minutos_estimados,
        "latitud_destino": float(e.latitud_destino) if e.latitud_destino else None,
        "longitud_destino": float(e.longitud_destino) if e.longitud_destino else None,
        "repartidor_id": e.repartidor_id,
        "repartidor_nombre": repartidor_nombre,
        "repartidor_lat": float(e.repartidor_lat) if e.repartidor_lat else None,
        "repartidor_lon": float(e.repartidor_lon) if e.repartidor_lon else None,
        "repartidor_actualizado_en": e.repartidor_actualizado_en.isoformat() if e.repartidor_actualizado_en else None,
        "token_seguimiento": e.token_seguimiento,
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
    import uuid
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

    token_seg = f"TRK-{uuid.uuid4().hex[:10].upper()}"

    envio = Envio(
        orden_venta_id=orden.id,
        direccion=dir_val,
        ciudad=payload.ciudad.strip() if payload.ciudad else "Santa Cruz",
        referencia=payload.referencia.strip() if payload.referencia else None,
        ubicacion_url=ub_url,
        costo=costo,
        estado="pendiente",
        fecha=datetime.now().date(),
        token_seguimiento=token_seg,
        tracking_activo=True,
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


from app.schemas.pago_envio import EnvioDeliveryUpdateRequest, EnvioYangoUpdateRequest


@router.patch("/{envio_id}/delivery", response_model=EnvioResponse, summary="Asignar o actualizar tracking de Delivery StyleStore")
@router.patch("/{envio_id}/yango", response_model=EnvioResponse, include_in_schema=False)
async def update_delivery_tracking(
    envio_id: int,
    payload: EnvioDeliveryUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Asigna repartidor, código de rastreo o actualiza estado del despacho Delivery StyleStore.
    """
    import uuid
    envio = db.query(Envio).filter(Envio.id == envio_id).first()
    if not envio:
        raise NotFoundException(f"Envío con ID {envio_id} no encontrado.")

    if not envio.token_seguimiento:
        envio.token_seguimiento = f"TRK-{uuid.uuid4().hex[:10].upper()}"

    code = payload.tracking_code or payload.yango_tracking_code
    if code is not None:
        envio.yango_tracking_code = code.strip()
    url = payload.tracking_url or payload.yango_tracking_url
    if url is not None:
        envio.yango_tracking_url = url.strip()
    if payload.delivery_conductor is not None:
        envio.delivery_conductor = payload.delivery_conductor.strip()
    if payload.estado is not None:
        envio.estado = payload.estado
    else:
        envio.estado = "en camino"

    if envio.estado in ["entregado", "completado"]:
        envio.tracking_activo = False
        if envio.orden_venta:
            envio.orden_venta.estado = "entregada"
    elif envio.orden_venta and envio.estado == "en camino":
        envio.tracking_activo = True
        envio.orden_venta.estado = "en camino"

    db.commit()
    db.refresh(envio)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Actualizó despacho Delivery para Envío #{envio.id} (Repartidor: {envio.delivery_conductor}, Estado: {envio.estado})",
        module="envios",
    )
    return _serialize_envio(envio)


# --- ENDPOINTS PÚBLICOS DE TRACKER (CONDUCTOR Y CLIENTE) ---


@router.get("/public/conductor/{token}", summary="Datos del pedido para el conductor")
async def get_pedido_conductor(token: str, db: Session = Depends(get_db)):
    """Permite al repartidor ver la dirección de entrega del cliente sin requerir autenticación."""
    envio = db.query(Envio).filter(Envio.token_seguimiento == token).first()
    if not envio:
        raise NotFoundException("Enlace de delivery no válido o expirado.")

    cli_name = "Cliente StyleStore"
    cli_tel = "No registrado"
    if envio.orden_venta and envio.orden_venta.cliente:
        cli = envio.orden_venta.cliente
        if cli.user:
            cli_name = f"{cli.user.name} {cli.user.apellido or ''}".strip()
        cli_tel = cli.telefono or cli_tel

    return {
        "envio_id": envio.id,
        "orden_venta_id": envio.orden_venta_id,
        "cliente_nombre": cli_name,
        "cliente_telefono": cli_tel,
        "direccion": envio.direccion,
        "ciudad": envio.ciudad,
        "referencia": envio.referencia,
        "ubicacion_url": envio.ubicacion_url,
        "estado": envio.estado,
        "tracking_activo": getattr(envio, "tracking_activo", True),
        "delivery_conductor": envio.delivery_conductor or "Conductor Asignado",
        "repartidor_lat": float(envio.repartidor_lat) if envio.repartidor_lat else None,
        "repartidor_lon": float(envio.repartidor_lon) if envio.repartidor_lon else None,
    }


@router.post("/public/conductor/{token}/posicion", summary="Transmitir ubicación GPS del conductor en tiempo real")
async def report_posicion_conductor(token: str, payload: dict, db: Session = Depends(get_db)):
    """El navegador móvil del conductor envía su latitud y longitud periódicamente."""
    envio = db.query(Envio).filter(Envio.token_seguimiento == token).first()
    if not envio:
        raise NotFoundException("Enlace de delivery no válido.")

    if not getattr(envio, "tracking_activo", True) or envio.estado in ["entregado", "completado"]:
        return {"activo": False, "message": "La entrega ya fue completada. Transmisión finalizada."}

    lat = payload.get("lat")
    lon = payload.get("lon")
    if lat is None or lon is None:
        raise BadRequestException("Se requieren lat y lon.")

    envio.repartidor_lat = Decimal(str(lat))
    envio.repartidor_lon = Decimal(str(lon))
    envio.repartidor_actualizado_en = datetime.now()

    if envio.estado == "pendiente":
        envio.estado = "en camino"
        if envio.orden_venta:
            envio.orden_venta.estado = "en camino"

    db.commit()
    return {"activo": True, "message": "Ubicación actualizada.", "lat": lat, "lon": lon}


@router.post("/public/conductor/{token}/entregar", summary="Marcar pedido entregado por el conductor")
async def marcar_entregado_conductor(token: str, db: Session = Depends(get_db)):
    """El repartidor confirma la entrega al cliente, cancelando la transmisión de GPS."""
    envio = db.query(Envio).filter(Envio.token_seguimiento == token).first()
    if not envio:
        raise NotFoundException("Enlace de delivery no válido.")

    envio.estado = "entregado"
    envio.tracking_activo = False
    if envio.orden_venta:
        envio.orden_venta.estado = "entregada"

    db.commit()
    return {"success": True, "message": "¡Pedido entregado con éxito! Transmisión de ubicación finalizada."}


@router.get("/public/rastreo/{token}", summary="Rastreo en vivo para el cliente con mapa OpenStreetMap")
async def get_rastreo_cliente(token: str, db: Session = Depends(get_db)):
    """Retorna coordenadas en tiempo real del conductor, origen y destino para el mapa del cliente."""
    from app.core.geo import geocodificar_aproximado
    envio = db.query(Envio).filter(Envio.token_seguimiento == token).first()
    if not envio:
        raise NotFoundException("Código o enlace de rastreo no encontrado.")

    orden = envio.orden_venta
    sucursal = orden.sucursal if orden else None

    if sucursal and sucursal.latitud and sucursal.longitud:
        orig_lat = float(sucursal.latitud)
        orig_lon = float(sucursal.longitud)
    else:
        orig_lat, orig_lon = geocodificar_aproximado(sucursal.ciudad if sucursal else envio.ciudad)

    dest_lat = float(envio.latitud_destino) if envio.latitud_destino else orig_lat + 0.015
    dest_lon = float(envio.longitud_destino) if envio.longitud_destino else orig_lon + 0.015

    rep_pos = None
    if envio.repartidor_lat and envio.repartidor_lon:
        rep_pos = {
            "lat": float(envio.repartidor_lat),
            "lon": float(envio.repartidor_lon),
            "actualizado_en": envio.repartidor_actualizado_en.isoformat() if envio.repartidor_actualizado_en else None,
        }

    return {
        "envio_id": envio.id,
        "orden_venta_id": envio.orden_venta_id,
        "estado": envio.estado,
        "tracking_activo": getattr(envio, "tracking_activo", True),
        "delivery_conductor": envio.delivery_conductor or "Repartidor Asignado",
        "distancia_km": float(envio.distancia_km) if envio.distancia_km else 3.5,
        "minutos_estimados": envio.minutos_estimados or 20,
        "origen": {
            "nombre": sucursal.nombre if sucursal else "Sucursal StyleStore",
            "ciudad": sucursal.ciudad if sucursal else envio.ciudad,
            "lat": orig_lat,
            "lon": orig_lon,
        },
        "destino": {
            "direccion": envio.direccion,
            "ciudad": envio.ciudad,
            "referencia": envio.referencia,
            "ubicacion_url": envio.ubicacion_url,
            "lat": dest_lat,
            "lon": dest_lon,
        },
        "repartidor": rep_pos,
    }


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


# ==============================================================
# ENDPOINTS DE DISTANCIA REAL Y ROL REPARTIDOR (v7 Punto 7)
# ==============================================================

@router.post("/cotizar-distancia", summary="Cotización de envío con distancia real Haversine")
async def cotizar_por_distancia(
    payload: dict,
    db: Session = Depends(get_db),
):
    """
    Calcula distancia real entre la sucursal de origen y el destino del cliente
    utilizando la fórmula de Haversine (R=6371 km).
    """
    from app.core.geo import calcular_cotizacion_completa, geocodificar_aproximado
    from app.models.sucursal import Sucursal

    sucursal_id = payload.get("sucursal_id")
    lat_dest = payload.get("lat")
    lon_dest = payload.get("lon")
    direccion = payload.get("direccion", "")
    ciudad = payload.get("ciudad", "la paz")

    # Obtener sucursal origen
    sucursal = None
    if sucursal_id:
        sucursal = db.query(Sucursal).filter(Sucursal.id == sucursal_id).first()
    if not sucursal:
        sucursal = db.query(Sucursal).first()

    # Coordenadas origen
    if sucursal and sucursal.latitud and sucursal.longitud:
        lat_orig = float(sucursal.latitud)
        lon_orig = float(sucursal.longitud)
    else:
        lat_orig, lon_orig = geocodificar_aproximado(sucursal.ciudad if sucursal else ciudad)

    # Coordenadas destino
    if lat_dest is not None and lon_dest is not None:
        lat_d = float(lat_dest)
        lon_d = float(lon_dest)
    else:
        lat_d, lon_d = geocodificar_aproximado(f"{direccion} {ciudad}")

    res = calcular_cotizacion_completa(lat_orig, lon_orig, lat_d, lon_d)
    res["sucursal_nombre"] = sucursal.nombre if sucursal else "Sucursal Central"
    res["sucursal_ciudad"] = sucursal.ciudad if sucursal else ciudad
    return res


@router.get("/asignados", summary="Envíos asignados al Repartidor")
async def list_envios_asignados(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna los envíos asignados al repartidor en sesión o pendientes."""
    if current_user.role == "repartidor":
        envios = (
            db.query(Envio)
            .filter(
                (Envio.repartidor_id == current_user.id) | (Envio.repartidor_id == None),
                Envio.estado.in_(["pendiente", "en camino"]),
            )
            .order_by(Envio.created_at.desc())
            .all()
        )
    else:
        envios = db.query(Envio).order_by(Envio.created_at.desc()).all()

    return [_serialize_envio(e) for e in envios]


@router.post("/{envio_id}/asignar", summary="Asignar repartidor a un envío")
async def asignar_repartidor(
    envio_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Asigna un usuario con rol repartidor a un envío."""
    envio = db.query(Envio).filter(Envio.id == envio_id).first()
    if not envio:
        raise NotFoundException(f"Envío #{envio_id} no encontrado.")

    repartidor_id = payload.get("repartidor_id") or current_user.id
    rep = db.query(User).filter(User.id == repartidor_id).first()
    if not rep:
        raise NotFoundException(f"Usuario repartidor #{repartidor_id} no encontrado.")

    envio.repartidor_id = rep.id
    envio.delivery_conductor = f"{rep.name} {rep.apellido or ''}".strip()
    if not envio.token_seguimiento:
        import uuid
        envio.token_seguimiento = f"TRK-{uuid.uuid4().hex[:10].upper()}"

    db.commit()
    db.refresh(envio)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Asignó el envío #{envio.id} al repartidor {envio.delivery_conductor}",
        module="envios",
    )
    return _serialize_envio(envio)


@router.patch("/{envio_id}/posicion", summary="Actualizar ubicación GPS del repartidor")
async def update_posicion_repartidor(
    envio_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Actualiza latitud y longitud en tiempo real del repartidor para el tracking."""
    envio = db.query(Envio).filter(Envio.id == envio_id).first()
    if not envio:
        raise NotFoundException(f"Envío #{envio_id} no encontrado.")

    lat = payload.get("lat")
    lon = payload.get("lon")
    if lat is None or lon is None:
        raise BadRequestException("Se requieren 'lat' y 'lon'.")

    envio.repartidor_lat = Decimal(str(lat))
    envio.repartidor_lon = Decimal(str(lon))
    envio.repartidor_actualizado_en = datetime.now()

    db.commit()
    return {"message": "Posición actualizada correctamente.", "lat": lat, "lon": lon}


@router.patch("/{envio_id}/estado", summary="Actualizar estado del despacho")
async def update_estado_despacho(
    envio_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permite al repartidor o staff cambiar estado a 'en camino', 'entregado', etc."""
    envio = db.query(Envio).filter(Envio.id == envio_id).first()
    if not envio:
        raise NotFoundException(f"Envío #{envio_id} no encontrado.")

    nuevo_estado = payload.get("estado")
    if not nuevo_estado:
        raise BadRequestException("Se requiere 'estado'.")

    envio.estado = nuevo_estado
    db.commit()

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Actualizó estado del envío #{envio.id} a '{nuevo_estado}'",
        module="envios",
    )
    return _serialize_envio(envio)


@router.get("/{envio_id}/tracking", summary="Obtener coordenadas y puntos para mapa Leaflet")
async def get_envio_tracking_map(
    envio_id: int,
    db: Session = Depends(get_db),
):
    """
    Retorna los datos de trazado para Leaflet + OpenStreetMap:
    Marcador de sucursal, marcador de destino y marcador de repartidor.
    """
    from app.core.geo import geocodificar_aproximado
    envio = db.query(Envio).filter(Envio.id == envio_id).first()
    if not envio:
        raise NotFoundException(f"Envío #{envio_id} no encontrado.")

    orden = envio.orden_venta
    sucursal = orden.sucursal if orden else None

    if sucursal and sucursal.latitud and sucursal.longitud:
        orig_lat = float(sucursal.latitud)
        orig_lon = float(sucursal.longitud)
    else:
        orig_lat, orig_lon = geocodificar_aproximado(sucursal.ciudad if sucursal else envio.ciudad)

    dest_lat = float(envio.latitud_destino) if envio.latitud_destino else orig_lat + 0.02
    dest_lon = float(envio.longitud_destino) if envio.longitud_destino else orig_lon + 0.02

    rep_pos = None
    if envio.repartidor_lat and envio.repartidor_lon:
        rep_pos = {
            "lat": float(envio.repartidor_lat),
            "lon": float(envio.repartidor_lon),
            "nombre": envio.delivery_conductor or "Repartidor en ruta",
            "actualizado_en": envio.repartidor_actualizado_en.isoformat() if envio.repartidor_actualizado_en else None,
        }

    return {
        "envio_id": envio.id,
        "estado": envio.estado,
        "token_seguimiento": envio.token_seguimiento,
        "distancia_km": float(envio.distancia_km) if envio.distancia_km else 3.5,
        "minutos_estimados": envio.minutos_estimados or 25,
        "origen": {
            "nombre": sucursal.nombre if sucursal else "Sucursal Central",
            "ciudad": sucursal.ciudad if sucursal else envio.ciudad,
            "lat": orig_lat,
            "lon": orig_lon,
        },
        "destino": {
            "direccion": envio.direccion,
            "ciudad": envio.ciudad,
            "referencia": envio.referencia,
            "lat": dest_lat,
            "lon": dest_lon,
        },
        "repartidor": rep_pos,
    }

