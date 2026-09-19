"""
Reservas endpoints (v5 sección 16).
Incluye transacción atómica con descuento automático de inventario.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.cliente import Cliente
from app.models.reserva import Reserva, DetalleReserva
from app.models.stock_inventario import StockInventario
from app.schemas.reserva import (
    ReservaCreate,
    ReservaResponse,
    ReservaEstadoUpdate,
    DetalleReservaResponse,
)
from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.bitacora_service import BitacoraService

router = APIRouter(prefix="/reservas", tags=["Reservas"])


def _serialize_reserva(res: Reserva) -> dict:
    detalles_resp = []
    for d in res.detalles:
        si = d.stock_inventario
        prod_cod = None
        prod_nom = None
        col_nom = None
        talla_nom = None
        foto = None
        if si:
            if si.producto_color:
                col_nom = si.producto_color.color.nombre if si.producto_color.color else None
                if si.producto_color.producto:
                    prod_cod = si.producto_color.producto.codigo
                    prod_nom = si.producto_color.producto.nombre
                    foto = si.producto_color.producto.foto
            if si.talla:
                talla_nom = si.talla.nombre

        detalles_resp.append({
            "id": d.id,
            "stock_inventario_id": d.stock_inventario_id,
            "cantidad": d.cantidad,
            "producto_codigo": prod_cod,
            "producto_nombre": prod_nom,
            "color_nombre": col_nom,
            "talla_nombre": talla_nom,
            "foto": foto,
        })

    cli_name = f"{res.cliente.user.name} {res.cliente.user.apellido or ''}".strip() if (res.cliente and res.cliente.user) else None

    return {
        "id": res.id,
        "fecha": res.fecha,
        "hora": res.hora,
        "estado": res.estado,
        "codigo_cliente": res.codigo_cliente,
        "cliente_nombre": cli_name,
        "sucursal_id": res.sucursal_id,
        "sucursal_ciudad": res.sucursal.ciudad if res.sucursal else None,
        "sucursal_direccion": res.sucursal.direccion if res.sucursal else None,
        "detalles": detalles_resp,
        "created_at": res.created_at,
    }


@router.get("", response_model=list[ReservaResponse], summary="Listar reservas (Administración y Clientes)")
async def list_reservas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Listado de reservas. Si es cliente retorna sus reservas, si es staff retorna todas."""
    if current_user.role == "cliente":
        cliente = db.query(Cliente).filter(Cliente.user_id == current_user.id).first()
        if not cliente:
            return []
        reservas = db.query(Reserva).filter(Reserva.codigo_cliente == cliente.codigo).order_by(Reserva.created_at.desc()).all()
        return [_serialize_reserva(r) for r in reservas]

    reservas = db.query(Reserva).order_by(Reserva.created_at.desc()).all()
    return [_serialize_reserva(r) for r in reservas]


@router.get("/mias", response_model=list[ReservaResponse], summary="Historial de reservas del cliente")
async def list_my_reservas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene el historial de reservas personales del cliente autenticado."""
    cliente = db.query(Cliente).filter(Cliente.user_id == current_user.id).first()
    if not cliente:
        return []
    reservas = db.query(Reserva).filter(Reserva.codigo_cliente == cliente.codigo).order_by(Reserva.created_at.desc()).all()
    return [_serialize_reserva(r) for r in reservas]


@router.get("/elegibilidad", summary="Verificar si el cliente actual puede realizar reservas")
async def verificar_elegibilidad_reserva(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verifica si el cliente tiene al menos 1 compra pagada para poder reservar prendas."""
    from app.models.orden_venta import OrdenVenta
    cliente = db.query(Cliente).filter(Cliente.user_id == current_user.id).first()
    if not cliente:
        return {
            "puede_reservar": False,
            "compras_previas": 0,
            "mensaje": "Aún no tienes compras registradas en StyleStore. Debes realizar al menos 1 compra pagada para habilitar reservas.",
        }

    compras_count = (
        db.query(OrdenVenta)
        .filter(
            OrdenVenta.codigo_cliente == cliente.codigo,
            OrdenVenta.estado.in_(["pagado", "pagada", "completado", "completada", "entregado", "entregada"]),
        )
        .count()
    )

    puede = compras_count > 0
    mensaje = (
        "¡Excelente! Tu cuenta está habilitada para reservar prendas sin costo previo."
        if puede
        else "Para habilitar la reserva de prendas en tienda, necesitas al menos 1 compra previa pagada."
    )

    return {
        "puede_reservar": puede,
        "compras_previas": compras_count,
        "mensaje": mensaje,
    }


@router.post("", response_model=ReservaResponse, status_code=status.HTTP_201_CREATED, summary="Crear reserva")
async def create_reserva(
    payload: ReservaCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea una reserva desde el catálogo descontando stock atómicamente (requiere ≥ 1 compra previa)."""
    from datetime import date, timedelta
    from app.models.orden_venta import OrdenVenta
    from app.services.notificacion_service import NotificacionService

    # Obtener o registrar cliente si no existe
    cliente = db.query(Cliente).filter(Cliente.user_id == current_user.id).first()
    if not cliente:
        clean_ci = current_user.ci or str(current_user.id).zfill(4)
        cod = f"CL-{current_user.name[:2].upper()}-{clean_ci[-4:]}"
        cliente = Cliente(
            codigo=cod,
            user_id=current_user.id,
            telefono=current_user.telefono or "00000000",
            direccion=current_user.direccion or "Sin dirección",
        )
        db.add(cliente)
        db.flush()

    # Validar regla de reserva: al menos 1 compra previa pagada (a excepción de rol administrador para pruebas)
    if current_user.role != "administrador":
        compras_previas = (
            db.query(OrdenVenta)
            .filter(
                OrdenVenta.codigo_cliente == cliente.codigo,
                OrdenVenta.estado.in_(["pagado", "pagada", "completado", "completada", "entregado", "entregada"]),
            )
            .count()
        )
        if compras_previas < 1:
            raise BadRequestException(
                "Solo los clientes con al menos 1 compra previa pagada pueden reservar prendas. ¡Realiza tu primera compra para desbloquear reservas exclusivas!"
            )

    # Validar duración máxima de 7 días
    hoy = date.today()
    max_fecha = hoy + timedelta(days=7)
    fecha_reserva = payload.fecha_limite or max_fecha
    if fecha_reserva < hoy or fecha_reserva > max_fecha:
        raise BadRequestException(
            f"La fecha de reserva no puede ser anterior a hoy ni superar el plazo máximo de 7 días ({max_fecha.strftime('%d/%m/%Y')})."
        )

    now = datetime.now()
    reserva = Reserva(
        fecha=fecha_reserva,
        hora=now.time(),
        estado="pendiente",
        codigo_cliente=cliente.codigo,
        sucursal_id=payload.sucursal_id,
    )
    db.add(reserva)
    db.flush()

    # Descuento atómico de stock por cada ítem
    for item in payload.items:
        stock = (
            db.query(StockInventario)
            .filter(StockInventario.id == item.stock_inventario_id)
            .with_for_update(of=StockInventario)
            .first()
        )
        if not stock:
            db.rollback()
            raise NotFoundException(f"Inventario con ID {item.stock_inventario_id} no encontrado.")

        if stock.cantidad < item.cantidad:
            db.rollback()
            raise BadRequestException(f"Stock insuficiente para el ítem {item.stock_inventario_id}. Disponible: {stock.cantidad}, solicitado: {item.cantidad}.")

        stock.cantidad -= item.cantidad
        detalle = DetalleReserva(
            reserva_id=reserva.id,
            stock_inventario_id=stock.id,
            cantidad=item.cantidad,
        )
        db.add(detalle)

    db.commit()
    db.refresh(reserva)

    try:
        notif_srv = NotificacionService(db)
        notif_srv.crear_notificacion(
            user_id=current_user.id,
            tipo="recordatorio_reserva",
            titulo="Reserva Registrada en StyleStore",
            mensaje=f"Tu reserva #{reserva.id} ha sido registrada. Vigencia hasta el {reserva.fecha.strftime('%d/%m/%Y')} para retirar en sucursal.",
            url_accion="/reservas",
            enviar_email=True,
        )
    except Exception:
        pass

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Registró la reserva #{reserva.id} para la sucursal #{reserva.sucursal_id}",
        module="reservas",
    )

    return _serialize_reserva(reserva)


@router.patch("/{reserva_id}/estado", response_model=ReservaResponse, summary="Actualizar estado de reserva")
async def update_reserva_estado(
    reserva_id: int,
    payload: ReservaEstadoUpdate,
    current_user: User = Depends(require_permission("reservas.editar")),
    db: Session = Depends(get_db),
):
    """Actualiza el estado de una reserva (ej. pendiente -> completada o cancelada)."""
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise NotFoundException(f"Reserva con ID {reserva_id} no encontrada.")

    # Si se cancela la reserva, restituir el stock
    if payload.estado == "cancelada" and reserva.estado != "cancelada":
        for d in reserva.detalles:
            stock = db.query(StockInventario).filter(StockInventario.id == d.stock_inventario_id).first()
            if stock:
                stock.cantidad += d.cantidad

    reserva.estado = payload.estado
    db.commit()
    db.refresh(reserva)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Actualizó el estado de la reserva #{reserva.id} a '{payload.estado}'",
        module="reservas",
    )

    return _serialize_reserva(reserva)


@router.delete("/{reserva_id}", summary="Eliminar o cancelar reserva")
async def delete_reserva(
    reserva_id: int,
    current_user: User = Depends(require_permission("reservas.eliminar")),
    db: Session = Depends(get_db),
):
    """Elimina una reserva y restituye el stock si estaba pendiente."""
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise NotFoundException(f"Reserva con ID {reserva_id} no encontrada.")

    if reserva.estado == "pendiente":
        for d in reserva.detalles:
            stock = db.query(StockInventario).filter(StockInventario.id == d.stock_inventario_id).first()
            if stock:
                stock.cantidad += d.cantidad

    db.delete(reserva)
    db.commit()

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Eliminó la reserva #{reserva_id}",
        module="reservas",
    )

    return {"message": f"Reserva #{reserva_id} eliminada exitosamente."}
