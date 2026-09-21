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
    """Tarifa oficial Delivery StyleStore: Tarifa fija 5 Bs + 0.60 Bs por km."""
    from app.core.geo import cotizar_costo_envio
    return cotizar_costo_envio(distancia_km)


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


@router.post("/cotizar", summary="Cotizar tarifa de envío Delivery StyleStore")
async def cotizar_envio(payload: EnvioCotizacionRequest):
    """Calcula el costo del envío: Tarifa fija 5 Bs + 0.60 Bs/km."""
    costo = _calcular_tarifa_escalonada(payload.distancia_km)
    return {
        "distancia_km": payload.distancia_km,
        "costo": costo,
        "tarifa_base": 5.00,
        "costo_por_km": 0.60,
        "moneda": "BOB",
    }


@router.post("", response_model=EnvioResponse, status_code=status.HTTP_201_CREATED, summary="Registrar envío")
async def create_envio(
    payload: EnvioCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea el registro de envío asociado a una orden de venta con tarifa fija 5 Bs + 0.60 Bs/km."""
    import uuid
    from app.core.geo import cotizar_costo_envio, extraer_coordenadas_de_url, calcular_distancia_haversine
    from app.models.sucursal import Sucursal

    orden = db.query(OrdenVenta).filter(OrdenVenta.id == payload.orden_venta_id).first()
    if not orden:
        raise NotFoundException(f"Orden de venta con ID {payload.orden_venta_id} no encontrada.")

    dir_val = payload.direccion.strip() if payload.direccion else ""
    ub_url = payload.ubicacion_url.strip() if payload.ubicacion_url else None
    if not dir_val and ub_url:
        dir_val = "Ubicación GPS (Ver enlace)"

    dest_lat = payload.latitud_destino
    dest_lon = payload.longitud_destino

    if dest_lat is None or dest_lon is None:
        if ub_url:
            dest_lat, dest_lon = extraer_coordenadas_de_url(ub_url)

    if dest_lat is None or dest_lon is None:
        texto_busqueda = f"{dir_val} {payload.referencia or ''} {payload.ciudad or ''}"
        dest_lat, dest_lon = geocodificar_aproximado(texto_busqueda)

    # Obtener sucursal de la orden para cálculo de origen
    sucursal = None
    if orden.sucursal_id:
        sucursal = db.query(Sucursal).filter(Sucursal.id == orden.sucursal_id).first()
    if not sucursal:
        sucursal = db.query(Sucursal).first()

    orig_lat = float(sucursal.latitud) if sucursal and sucursal.latitud else None
    orig_lon = float(sucursal.longitud) if sucursal and sucursal.longitud else None
    if (orig_lat is None or orig_lon is None) and sucursal and sucursal.maps_url:
        orig_lat, orig_lon = extraer_coordenadas_de_url(sucursal.maps_url)
    if orig_lat is None or orig_lon is None:
        orig_lat, orig_lon = geocodificar_aproximado(sucursal.ciudad if sucursal else "Santa Cruz")

    dist_calc = payload.distancia_km
    if dist_calc is None and dest_lat is not None and dest_lon is not None and orig_lat is not None and orig_lon is not None:
        dist_calc = calcular_distancia_haversine(orig_lat, orig_lon, dest_lat, dest_lon)

    # Calcular costo según tarifa oficial: 5 Bs fija base + 0.60 Bs/km
    if payload.costo is not None and payload.costo > 0:
        costo = payload.costo
    elif dist_calc is not None:
        costo = cotizar_costo_envio(dist_calc)
    else:
        costo = Decimal("5.00")

    # Sumar costo de envío al total de la orden de venta si no estaba ya contemplado
    if costo and costo > 0:
        orden.total = (orden.total or Decimal("0.00")) + costo

    token_seg = f"TRK-{uuid.uuid4().hex[:10].upper()}"

    envio = Envio(
        orden_venta_id=orden.id,
        direccion=dir_val,
        ciudad=payload.ciudad.strip() if payload.ciudad else "Santa Cruz",
        referencia=payload.referencia.strip() if payload.referencia else None,
        ubicacion_url=ub_url,
        latitud_destino=dest_lat,
        longitud_destino=dest_lon,
        distancia_km=Decimal(str(round(dist_calc, 2))) if dist_calc is not None else None,
        minutos_estimados=max(15, int((dist_calc or 0) * 2.5) + 15),
        costo=costo,
        estado="pendiente",
        fecha=datetime.now().date(),
        token_seguimiento=token_seg,
        tracking_activo=True,
    )

    try:
        db.add(envio)
        db.commit()
        db.refresh(envio)
    except Exception:
        # Recuperación defensiva automática si alguna columna de la migración no existía aún en la BD
        db.rollback()
        from app.init_db import _run_column_migrations
        _run_column_migrations(db)
        db.add(envio)
        db.commit()
        db.refresh(envio)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Registró envío #{envio.id} a {envio.ciudad} para Orden #{orden.id} (Costo Delivery: Bs {envio.costo})",
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
    from app.core.geo import geocodificar_aproximado, calcular_distancia_haversine, estimar_tiempo_entrega
    envio = db.query(Envio).filter(Envio.token_seguimiento == token).first()
    if not envio:
        raise NotFoundException("Código o enlace de rastreo no encontrado.")

    orden = envio.orden_venta
    sucursal = orden.sucursal if orden else None

    if sucursal and sucursal.latitud and sucursal.longitud:
        orig_lat = float(sucursal.latitud)
        orig_lon = float(sucursal.longitud)
    elif sucursal and sucursal.maps_url:
        orig_lat, orig_lon = extraer_coordenadas_de_url(sucursal.maps_url)
    else:
        orig_lat, orig_lon = None, None

    if orig_lat is None or orig_lon is None:
        orig_lat, orig_lon = geocodificar_aproximado(sucursal.ciudad if sucursal else (envio.ciudad or "Santa Cruz"))

    dest_lat = float(envio.latitud_destino) if envio.latitud_destino else None
    dest_lon = float(envio.longitud_destino) if envio.longitud_destino else None

    # Si no tiene coordenadas de destino guardadas en la BD, extraerlas de la URL o geocodificar por dirección
    if dest_lat is None or dest_lon is None:
        if envio.ubicacion_url:
            dest_lat, dest_lon = extraer_coordenadas_de_url(envio.ubicacion_url)
        if dest_lat is None or dest_lon is None:
            texto_busqueda = f"{envio.direccion or ''} {envio.referencia or ''} {envio.ciudad or ''}"
            dest_lat, dest_lon = geocodificar_aproximado(texto_busqueda)

        # Persistir las coordenadas recuperadas para futuros accesos
        if dest_lat is not None and dest_lon is not None:
            envio.latitud_destino = Decimal(str(round(dest_lat, 6)))
            envio.longitud_destino = Decimal(str(round(dest_lon, 6)))
            db.commit()

    # Fallback seguro absoluto garantizando siempre coordenadas válidas
    if dest_lat is None or dest_lon is None:
        dest_lat, dest_lon = geocodificar_aproximado(envio.ciudad or "Santa Cruz")

    rep_pos = None
    distancia_actual = float(envio.distancia_km) if envio.distancia_km else 3.5
    minutos_actual = envio.minutos_estimados or 20

    if envio.repartidor_lat and envio.repartidor_lon:
        r_lat = float(envio.repartidor_lat)
        r_lon = float(envio.repartidor_lon)

        # Validar coherencia de ciudad entre el repartidor y el destino
        dist_al_destino = calcular_distancia_haversine(r_lat, r_lon, dest_lat, dest_lon)
        # Si la coordenada guardada quedó en otra ciudad (> 80 km, ej: La Paz vs Santa Cruz)
        if dist_al_destino > 80.0:
            # Reubicar al repartidor en la ciudad correcta partiendo desde la sucursal
            r_lat = orig_lat + 0.003
            r_lon = orig_lon + 0.003
            dist_al_destino = calcular_distancia_haversine(r_lat, r_lon, dest_lat, dest_lon)
            envio.repartidor_lat = Decimal(str(round(r_lat, 6)))
            envio.repartidor_lon = Decimal(str(round(r_lon, 6)))
            db.commit()

        rep_pos = {
            "lat": r_lat,
            "lon": r_lon,
            "actualizado_en": envio.repartidor_actualizado_en.isoformat() if envio.repartidor_actualizado_en else None,
        }
        # Cálculo dinámico del trayecto restante según la posición del repartidor en vivo
        distancia_actual = round(dist_al_destino, 2)
        minutos_actual = estimar_tiempo_entrega(dist_al_destino)

    return {
        "envio_id": envio.id,
        "orden_venta_id": envio.orden_venta_id,
        "estado": envio.estado,
        "tracking_activo": getattr(envio, "tracking_activo", True),
        "delivery_conductor": envio.delivery_conductor or "Repartidor Asignado",
        "distancia_km": distancia_actual,
        "minutos_estimados": minutos_actual,
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
    utilizando la fórmula de Haversine (R=6371 km) y tarifa oficial StyleStore (5 Bs + 0.60 Bs/km).
    Compara las dos ubicaciones (origen en sucursal vs destino del cliente).
    """
    from app.core.geo import (
        calcular_distancia_haversine,
        estimar_tiempo_entrega,
        geocodificar_aproximado,
        extraer_coordenadas_de_url,
    )
    from app.models.sucursal import Sucursal

    sucursal_id = payload.get("sucursal_id")
    sucursal_maps_url_in = payload.get("sucursal_maps_url")
    sucursal_nombre_in = payload.get("sucursal_nombre")
    lat_dest = payload.get("lat")
    lon_dest = payload.get("lon")
    ubicacion_url = payload.get("ubicacion_url")
    direccion = payload.get("direccion", "")
    ciudad = payload.get("ciudad", "santa cruz")

    # 1. Obtener sucursal de origen
    sucursal = None
    if sucursal_id:
        sucursal = db.query(Sucursal).filter(Sucursal.id == sucursal_id).first()
    if not sucursal and sucursal_nombre_in:
        sucursal = db.query(Sucursal).filter(Sucursal.nombre.ilike(f"%{sucursal_nombre_in}%")).first()
    if not sucursal:
        sucursal = db.query(Sucursal).first()

    # 2. Determinar coordenadas de la Sucursal (Origen)
    lat_orig, lon_orig = None, None
    maps_url_suc = sucursal_maps_url_in or (getattr(sucursal, "maps_url", None) if sucursal else None)

    if sucursal and sucursal.latitud and sucursal.longitud:
        try:
            lat_orig = float(sucursal.latitud)
            lon_orig = float(sucursal.longitud)
        except (ValueError, TypeError):
            pass

    if (lat_orig is None or lon_orig is None) and maps_url_suc:
        lat_s, lon_s = extraer_coordenadas_de_url(maps_url_suc)
        if lat_s is not None and lon_s is not None:
            lat_orig, lon_orig = lat_s, lon_s

    if lat_orig is None or lon_orig is None:
        query_suc = f"{sucursal.nombre if sucursal else (sucursal_nombre_in or '')} {sucursal.direccion if sucursal else ''} {sucursal.ciudad if sucursal else ciudad}"
        lat_orig, lon_orig = geocodificar_aproximado(query_suc)

    # Persistir coordenadas y maps_url si no los tenía
    if sucursal:
        if lat_orig and lon_orig and (not sucursal.latitud or not sucursal.longitud):
            sucursal.latitud = Decimal(str(round(lat_orig, 6)))
            sucursal.longitud = Decimal(str(round(lon_orig, 6)))
        if maps_url_suc and not sucursal.maps_url:
            sucursal.maps_url = maps_url_suc
        elif not sucursal.maps_url and lat_orig and lon_orig:
            sucursal.maps_url = f"https://maps.google.com/?q={lat_orig},{lon_orig}"
        try:
            db.commit()
        except Exception:
            db.rollback()

    sucursal_final_maps_url = (
        getattr(sucursal, "maps_url", None)
        or maps_url_suc
        or (f"https://maps.google.com/?q={lat_orig},{lon_orig}" if lat_orig and lon_orig else None)
    )

    # 3. Determinar coordenadas del Cliente (Destino)
    if (lat_dest is None or lon_dest is None) and ubicacion_url:
        lat_u, lon_u = extraer_coordenadas_de_url(ubicacion_url)
        if lat_u is not None and lon_u is not None:
            lat_dest, lon_dest = lat_u, lon_u

    if lat_dest is not None and lon_dest is not None:
        lat_d = float(lat_dest)
        lon_d = float(lon_dest)
    else:
        # Geocodificar a partir de la dirección escrita y ciudad
        query_cli = f"{direccion} {ciudad}".strip()
        lat_d, lon_d = geocodificar_aproximado(query_cli if query_cli else "santa cruz sirari")

    # 4. Calcular distancia Haversine entre Sucursal y Destino
    distancia = calcular_distancia_haversine(lat_orig, lon_orig, lat_d, lon_d)

    # Si la distancia es virtualmente cero (ambas coordenadas cayeron en el mismo punto genérico)
    if distancia < 0.2:
        distancia = 3.50

    # 5. Tarifa oficial StyleStore: 5.00 Bs base fija + 0.60 Bs por km
    costo_envio = round(5.00 + (distancia * 0.60), 2)
    minutos = estimar_tiempo_entrega(distancia)

    nombre_suc = sucursal.nombre if sucursal else (sucursal_nombre_in or "Sucursal Central")

    return {
        "distancia_km": distancia,
        "costo": costo_envio,
        "costo_envio": costo_envio,
        "tarifa_base": 5.00,
        "costo_por_km": 0.60,
        "moneda": "BOB",
        "minutos_estimados": minutos,
        "sucursal_id": sucursal.id if sucursal else None,
        "sucursal_nombre": nombre_suc,
        "sucursal_ciudad": sucursal.ciudad if sucursal else ciudad,
        "sucursal_direccion": sucursal.direccion if sucursal else "",
        "sucursal_maps_url": sucursal_final_maps_url,
        "origen": {"lat": lat_orig, "lon": lon_orig, "nombre": nombre_suc},
        "destino": {"lat": lat_d, "lon": lon_d, "direccion": direccion, "ubicacion_url": ubicacion_url},
        "comparacion_texto": f"Ruta de despacho: desde {nombre_suc} hasta tu destino ({distancia} km)",
    }


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
    from app.core.geo import geocodificar_aproximado, calcular_distancia_haversine, estimar_tiempo_entrega
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
    distancia_actual = float(envio.distancia_km) if envio.distancia_km else 3.5
    minutos_actual = envio.minutos_estimados or 25

    if envio.repartidor_lat and envio.repartidor_lon:
        r_lat = float(envio.repartidor_lat)
        r_lon = float(envio.repartidor_lon)
        dist_al_destino = calcular_distancia_haversine(r_lat, r_lon, dest_lat, dest_lon)
        if dist_al_destino > 80.0:
            r_lat = orig_lat + 0.003
            r_lon = orig_lon + 0.003
            dist_al_destino = calcular_distancia_haversine(r_lat, r_lon, dest_lat, dest_lon)
            envio.repartidor_lat = Decimal(str(round(r_lat, 6)))
            envio.repartidor_lon = Decimal(str(round(r_lon, 6)))
            db.commit()

        rep_pos = {
            "lat": r_lat,
            "lon": r_lon,
            "nombre": envio.delivery_conductor or "Repartidor en ruta",
            "actualizado_en": envio.repartidor_actualizado_en.isoformat() if envio.repartidor_actualizado_en else None,
        }
        distancia_actual = round(dist_al_destino, 2)
        minutos_actual = estimar_tiempo_entrega(dist_al_destino)

    return {
        "envio_id": envio.id,
        "estado": envio.estado,
        "token_seguimiento": envio.token_seguimiento,
        "distancia_km": distancia_actual,
        "minutos_estimados": minutos_actual,
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

