"""
Pagos endpoints (v5 sección 19 y 22).
Soporta procesamiento de pago con PayPal (online) y caja presencial, emitiendo recibo de venta.
"""
from decimal import Decimal
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.cliente import Cliente
from app.models.orden_venta import OrdenVenta
from app.models.pago import Pago
from app.schemas.pago_envio import PagoCreateRequest, PagoResponse
from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.bitacora_service import BitacoraService

router = APIRouter(prefix="/pagos", tags=["Pagos"])


@router.post("", response_model=PagoResponse, status_code=status.HTTP_201_CREATED, summary="Procesar pago (PayPal / Caja)")
async def process_payment(
    payload: PagoCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Registra el pago de una orden de venta:
    - En línea: integra/simula PayPal registrando paypal_order_id.
    - En caja: cobro presencial en punto de venta.
    Actualiza la orden de venta a estado 'pagada'.
    """
    orden = db.query(OrdenVenta).filter(OrdenVenta.id == payload.orden_venta_id).first()
    if not orden:
        raise NotFoundException(f"Orden de venta con ID {payload.orden_venta_id} no encontrada.")

    # Generar o asignar paypal_order_id
    pp_id = payload.paypal_order_id or f"PAYPAL-SIM-{orden.id}"

    pago = Pago(
        orden_venta_id=orden.id,
        monto=orden.total,
        tipo_pago=payload.tipo_pago,
        estado="aprobado",
        paypal_order_id=pp_id,
    )
    db.add(pago)

    orden.estado = "pagada"
    db.commit()
    db.refresh(pago)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Registró pago #{pago.id} ({pago.tipo_pago}) por Bs {pago.monto} para Orden #{orden.id}",
        module="pagos",
    )

    return pago


@router.get("/mios", response_model=list[PagoResponse], summary="Historial de pagos del cliente (v5 sección 22)")
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
        "cliente_codigo": orden.codigo_cliente if orden else None,
        "items": items,
        "total": orden.total if orden else pago.monto,
    }
