"""
Pagos endpoints (v5 sección 19 y 22, Guía de Pagos & Caja POS).
Soporta:
- PayPal Orders v2 (crear orden y capturar fondos con idempotencia).
- Caja / Cobro presencial en efectivo con cálculo de vuelto y tickets de venta.
- Consulta de recibos / historial.
"""
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.cliente import Cliente
from app.models.orden_venta import OrdenVenta
from app.models.pago import Pago
from app.schemas.pago_envio import (
    PagoCreateRequest,
    PagoResponse,
    PayPalCrearOrdenRequest,
    PayPalCapturarOrdenRequest,
    CobroCajaRequest,
    CobroCajaResponse,
)
from app.api.deps import get_current_user, get_optional_current_user, require_permission
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.bitacora_service import BitacoraService
from app.services.paypal_service import paypal_service

router = APIRouter(prefix="/pagos", tags=["Pagos"])


# ==========================================
# 1. PAYPAL ORDERS V2
# ==========================================

@router.post("/paypal/crear-orden", summary="Crear orden en PayPal Orders v2")
async def create_paypal_order(
    payload: PayPalCrearOrdenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Crea una orden en PayPal v2 para el checkout de StyleStore.
    """
    orden = db.query(OrdenVenta).filter(OrdenVenta.id == payload.orden_venta_id).first()
    if not orden:
        raise NotFoundException(f"Orden de venta con ID {payload.orden_venta_id} no encontrada.")

    if orden.estado == "pagada":
        raise BadRequestException("Esta orden ya ha sido pagada previamente.")

    order_data = await paypal_service.create_order(
        orden_id=orden.id,
        total=orden.total,
        return_url=payload.return_url or "",
        cancel_url=payload.cancel_url or "",
    )

    paypal_order_id = order_data.get("id")

    # Crear o actualizar registro provisional de pago
    pago_existente = db.query(Pago).filter(Pago.orden_venta_id == orden.id).first()
    if not pago_existente:
        pago_existente = Pago(
            orden_venta_id=orden.id,
            monto=orden.total,
            tipo_pago="en linea",
            estado="pendiente",
            paypal_order_id=paypal_order_id,
        )
        db.add(pago_existente)
    else:
        pago_existente.paypal_order_id = paypal_order_id
        pago_existente.tipo_pago = "en linea"
        pago_existente.estado = "pendiente"

    db.commit()

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Inició checkout con PayPal para Orden #{orden.id} (PayPal ID: {paypal_order_id})",
        module="pagos",
    )

    return order_data


@router.post("/paypal/capturar-orden", response_model=PagoResponse, summary="Capturar fondos de PayPal")
async def capture_paypal_order(
    payload: PayPalCapturarOrdenRequest,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Captura los fondos tras la aprobación del cliente en PayPal.
    Implementa idempotencia para evitar errores si la orden ya fue procesada,
    y resuelve la orden automáticamente si se proporciona solo el token de PayPal.
    """
    orden = None
    pago = None

    # 1. Buscar orden por ID si fue provisto
    if payload.orden_venta_id and payload.orden_venta_id > 0:
        orden = db.query(OrdenVenta).filter(OrdenVenta.id == payload.orden_venta_id).first()

    # 2. Si no se encontró por ID, buscar pago por paypal_order_id
    if not orden or not pago:
        pago = db.query(Pago).filter(Pago.paypal_order_id == payload.paypal_order_id).first()
        if pago and not orden:
            orden = db.query(OrdenVenta).filter(OrdenVenta.id == pago.orden_venta_id).first()

    # 3. Si aún no tenemos orden, buscar la última orden pendiente del sistema o cliente
    if not orden:
        orden = db.query(OrdenVenta).order_by(OrdenVenta.id.desc()).first()

    if not orden:
        raise NotFoundException("No se encontró ninguna orden de venta asociada al token de PayPal.")

    if not pago:
        pago = db.query(Pago).filter(Pago.orden_venta_id == orden.id).first()

    # Si ya está aprobada, retornar directamente (idempotencia)
    if pago and pago.estado == "aprobado" and pago.paypal_capture_id:
        return pago

    # Llamar a PayPal para capturar fondos
    capture_res = await paypal_service.capture_order(payload.paypal_order_id)
    status_capture = capture_res.get("status")

    if status_capture not in ["COMPLETED", "SAVED"]:
        raise BadRequestException(f"No se pudo completar el pago con PayPal: {capture_res.get('error', 'Rechazado')}")

    # Extraer capture ID
    capture_id = payload.paypal_order_id
    try:
        units = capture_res.get("purchase_units", [])
        if units and "payments" in units[0] and "captures" in units[0]["payments"]:
            capture_id = units[0]["payments"]["captures"][0].get("id", capture_id)
    except Exception:
        pass

    if not pago:
        pago = Pago(
            orden_venta_id=orden.id,
            monto=orden.total,
            tipo_pago="en linea",
            estado="aprobado",
            paypal_order_id=payload.paypal_order_id,
            paypal_capture_id=capture_id,
        )
        db.add(pago)
    else:
        pago.estado = "aprobado"
        pago.paypal_order_id = payload.paypal_order_id
        pago.paypal_capture_id = capture_id

    orden.estado = "pagada"
    orden.metodo_pago = "paypal"
    db.commit()
    db.refresh(pago)

    # Registro en Bitácora con fallback seguro de usuario
    user_audit = current_user
    if not user_audit:
        cliente = db.query(Cliente).filter(Cliente.codigo == orden.codigo_cliente).first()
        if cliente and cliente.user_id:
            user_audit = db.query(User).filter(User.id == cliente.user_id).first()

    if user_audit:
        BitacoraService.registrar(
            db=db,
            user=user_audit,
            action=f"Completó pago exitoso con PayPal ({capture_id}) para Orden #{orden.id}",
            module="pagos",
        )

    return pago


# ==========================================
# 2. COBRO EN CAJA (POS / EFECTIVO)
# ==========================================

@router.post("/caja", response_model=CobroCajaResponse, summary="Procesar cobro en caja con cálculo de vuelto")
async def process_caja_payment(
    payload: CobroCajaRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Registra cobro en efectivo presencial en el POS / Punto de Venta.
    Calcula vuelto y genera ticket numerado de venta.
    """
    orden = db.query(OrdenVenta).filter(OrdenVenta.id == payload.orden_venta_id).first()
    if not orden:
        raise NotFoundException(f"Orden de venta con ID {payload.orden_venta_id} no encontrada.")

    if orden.estado == "pagada":
        raise BadRequestException("Esta orden ya ha sido cobrada y está pagada.")

    if payload.efectivo_recibido < orden.total:
        diff = orden.total - payload.efectivo_recibido
        raise BadRequestException(f"El monto recibido (Bs. {payload.efectivo_recibido}) es inferior al total a pagar (Bs. {orden.total}). Faltan: Bs. {diff}")

    cambio = payload.efectivo_recibido - orden.total
    ticket_num = f"TKT-{datetime.now().strftime('%Y%m%d')}-{orden.id:04d}"

    orden.estado = "pagada"
    orden.metodo_pago = "efectivo"
    orden.ticket_numero = ticket_num
    orden.efectivo_recibido = payload.efectivo_recibido
    orden.cambio_devuelto = cambio

    pago = db.query(Pago).filter(Pago.orden_venta_id == orden.id).first()
    if not pago:
        pago = Pago(
            orden_venta_id=orden.id,
            monto=orden.total,
            tipo_pago="en caja",
            estado="aprobado",
        )
        db.add(pago)
    else:
        pago.tipo_pago = "en caja"
        pago.estado = "aprobado"

    db.commit()
    db.refresh(pago)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Emitió ticket de caja {ticket_num} para Orden #{orden.id}. Recibido: Bs. {payload.efectivo_recibido}, Cambio: Bs. {cambio}",
        module="pagos",
    )

    return CobroCajaResponse(
        pago_id=pago.id,
        orden_venta_id=orden.id,
        total=orden.total,
        efectivo_recibido=payload.efectivo_recibido,
        cambio_devuelto=cambio,
        ticket_numero=ticket_num,
        fecha=datetime.now(),
    )


# ==========================================
# 3. PROCESAR PAGO GENÉRICO / HISTORIAL
# ==========================================

@router.post("", response_model=PagoResponse, status_code=status.HTTP_201_CREATED, summary="Procesar pago general")
async def process_payment(
    payload: PagoCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Registra el pago general de una orden de venta.
    """
    orden = db.query(OrdenVenta).filter(OrdenVenta.id == payload.orden_venta_id).first()
    if not orden:
        raise NotFoundException(f"Orden de venta con ID {payload.orden_venta_id} no encontrada.")

    pp_id = payload.paypal_order_id or f"PAYPAL-SIM-{orden.id}"

    pago = Pago(
        orden_venta_id=orden.id,
        monto=orden.total,
        tipo_pago=payload.tipo_pago,
        estado="aprobado",
        paypal_order_id=pp_id,
        paypal_capture_id=payload.paypal_capture_id,
    )
    db.add(pago)

    orden.estado = "pagada"
    orden.metodo_pago = payload.tipo_pago
    db.commit()
    db.refresh(pago)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Registró pago #{pago.id} ({pago.tipo_pago}) por ${pago.monto} para Orden #{orden.id}",
        module="pagos",
    )

    return pago


@router.get("/mios", response_model=list[PagoResponse], summary="Historial de pagos del cliente")
async def list_my_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene el historial de pagos del cliente en sesión."""
    cliente = db.query(Cliente).filter(Cliente.user_id == current_user.id).first()
    if not cliente:
        return []

    pagos = (
        db.query(Pago)
        .join(OrdenVenta, Pago.orden_venta_id == OrdenVenta.id)
        .filter(OrdenVenta.codigo_cliente == cliente.codigo)
        .order_by(Pago.created_at.desc())
        .all()
    )
    return pagos


@router.get("/{pago_id}", summary="Obtener recibo / nota de venta")
async def get_payment_receipt(
    pago_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Genera el detalle completo de recibo / nota de venta."""
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise NotFoundException(f"Pago con ID {pago_id} no encontrado.")

    orden = pago.orden_venta
    items = []
    if orden:
        for d in orden.detalles:
            items.append({
                "producto": d.producto_nombre,
                "color": d.color_nombre,
                "talla": d.talla_nombre,
                "cantidad": d.cantidad,
                "precio_unitario": d.precio_unitario,
                "subtotal": d.subtotal,
            })

    return {
        "pago_id": pago.id,
        "orden_venta_id": pago.orden_venta_id,
        "fecha": pago.created_at,
        "monto": pago.monto,
        "tipo_pago": pago.tipo_pago,
        "estado": pago.estado,
        "paypal_order_id": pago.paypal_order_id,
        "paypal_capture_id": pago.paypal_capture_id,
        "ticket_numero": orden.ticket_numero if orden else None,
        "efectivo_recibido": orden.efectivo_recibido if orden else None,
        "cambio_devuelto": orden.cambio_devuelto if orden else None,
        "cliente_codigo": orden.codigo_cliente if orden else None,
        "items": items,
        "total": orden.total if orden else pago.monto,
    }
