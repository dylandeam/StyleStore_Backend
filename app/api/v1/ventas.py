"""
Ventas endpoints (v5 secciones 18, 21 y 23).
Gestión de ventas presenciales y en línea, e historial de compras del cliente.
"""
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.cliente import Cliente
from app.models.orden_venta import OrdenVenta, DetalleVenta
from app.models.pago import Pago
from app.models.stock_inventario import StockInventario
from app.schemas.pago_envio import (
    OrdenVentaResponse,
    VentaPresencialCreate,
    DetalleVentaResponse,
)
from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.bitacora_service import BitacoraService

router = APIRouter(prefix="/ventas", tags=["Ventas"])


def _serialize_orden(o: OrdenVenta) -> dict:
    detalles = []
    for d in o.detalles:
        prod_cod = None
        if d.stock_inventario and d.stock_inventario.producto_color:
            prod_cod = d.stock_inventario.producto_color.producto_codigo
        detalles.append({
            "id": d.id,
            "stock_inventario_id": d.stock_inventario_id,
            "producto_codigo": prod_cod,
            "producto_nombre": d.producto_nombre,
            "color_nombre": d.color_nombre,
            "talla_nombre": d.talla_nombre,
            "cantidad": d.cantidad,
            "precio_unitario": d.precio_unitario,
            "subtotal": d.subtotal,
        })

    cli_nom = None
    cli_email = None
    cli_tel = None
    if o.cliente:
        cli_tel = o.cliente.telefono
        if o.cliente.user:
            u = o.cliente.user
            cli_nom = f"{u.name} {u.apellido or ''}".strip()
            cli_email = u.email

    envio_dict = None
    if o.envios:
        env = o.envios[0]
        envio_dict = {
            "id": env.id,
            "orden_venta_id": env.orden_venta_id,
            "direccion": env.direccion,
            "ciudad": env.ciudad,
            "referencia": env.referencia,
            "costo": env.costo,
            "estado": env.estado,
            "fecha": env.fecha,
            "created_at": env.created_at,
            "cliente_nombre": cli_nom,
            "yango_tracking_code": getattr(env, "yango_tracking_code", None),
            "yango_tracking_url": getattr(env, "yango_tracking_url", None),
            "delivery_conductor": getattr(env, "delivery_conductor", None),
        }

    return {
        "id": o.id,
        "fecha": o.fecha,
        "estado": o.estado,
        "total": o.total,
        "tipo_venta": o.tipo_venta,
        "metodo_pago": o.metodo_pago,
        "ticket_numero": o.ticket_numero,
        "codigo_cliente": o.codigo_cliente,
        "cliente_nombre": cli_nom,
        "cliente_email": cli_email,
        "cliente_telefono": cli_tel,
        "sucursal_ciudad": o.sucursal.ciudad if o.sucursal else None,
        "sucursal_nombre": o.sucursal.nombre if o.sucursal else None,
        "sucursal_direccion": o.sucursal.direccion if o.sucursal else None,
        "sucursal_id": o.sucursal_id,
        "detalles": detalles,
        "envio": envio_dict,
        "created_at": o.created_at,
    }


@router.get("", response_model=list[OrdenVentaResponse], summary="Listar ventas combinadas (Administración y Clientes)")
async def list_ventas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista combinada de ventas. Si es cliente retorna sus compras, si es staff retorna todas."""
    if current_user.role == "cliente":
        cliente = db.query(Cliente).filter(Cliente.user_id == current_user.id).first()
        if not cliente:
            return []
        ventas = db.query(OrdenVenta).filter(OrdenVenta.codigo_cliente == cliente.codigo).order_by(OrdenVenta.created_at.desc()).all()
        return [_serialize_orden(v) for v in ventas]

    ventas = db.query(OrdenVenta).order_by(OrdenVenta.created_at.desc()).all()
    return [_serialize_orden(v) for v in ventas]


@router.get("/mias", summary="Historial de compras del cliente (v5 sección 21)")
async def list_my_purchases(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve las compras del cliente separadas en:
    - compras_carrito: Compras en línea vía carrito.
    - compras_presenciales: Compras presenciales en tienda física.
    """
    cliente = db.query(Cliente).filter(Cliente.user_id == current_user.id).first()
    if not cliente:
        return {"compras_carrito": [], "compras_presenciales": []}

    ventas = db.query(OrdenVenta).filter(OrdenVenta.codigo_cliente == cliente.codigo).order_by(OrdenVenta.created_at.desc()).all()

    carrito_list = [_serialize_orden(v) for v in ventas if v.tipo_venta == "en linea"]
    presenciales_list = [_serialize_orden(v) for v in ventas if v.tipo_venta == "presencial"]

    return {
        "compras_carrito": carrito_list,
        "compras_presenciales": presenciales_list,
    }


@router.get("/mis-compras", response_model=list[OrdenVentaResponse], summary="Historial de compras para aplicación móvil y web")
async def list_mis_compras(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve la lista unificada de todas las órdenes de venta del cliente actual."""
    cliente = db.query(Cliente).filter(Cliente.user_id == current_user.id).first()
    if not cliente:
        return []

    ventas = db.query(OrdenVenta).filter(OrdenVenta.codigo_cliente == cliente.codigo).order_by(OrdenVenta.created_at.desc()).all()
    return [_serialize_orden(v) for v in ventas]


@router.get("/{venta_id}", response_model=OrdenVentaResponse, summary="Detalle de venta")
async def get_venta(
    venta_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detalle completo de una orden de venta."""
    venta = db.query(OrdenVenta).filter(OrdenVenta.id == venta_id).first()
    if not venta:
        raise NotFoundException(f"Venta con ID {venta_id} no encontrada.")
    return _serialize_orden(venta)


@router.post("/presencial", response_model=OrdenVentaResponse, status_code=status.HTTP_201_CREATED, summary="Registrar venta presencial en caja")
async def create_venta_presencial(
    payload: VentaPresencialCreate,
    current_user: User = Depends(require_permission("productos.editar")),
    db: Session = Depends(get_db),
):
    """
    Registra una compra presencial desde caja:
    - Descuenta existencias en inventario atómicamente.
    - Genera la OrdenVenta y DetalleVenta.
    - Registra el Pago en caja inmediatamente.
    """
    # Buscar cliente o asignar/crear Cliente General por defecto
    codigo_cli = payload.codigo_cliente or "CLI-GENERAL"
    cliente = db.query(Cliente).filter(Cliente.codigo == codigo_cli).first()
    if not cliente:
        # Intentar buscar por id o crear un cliente genérico para ventas rápidas de mostrador
        cliente = db.query(Cliente).first()
        if not cliente:
            cliente = Cliente(
                codigo="CLI-GENERAL",
                user_id=current_user.id,
                telefono="00000000",
                direccion="Venta Mostrador",
            )
            db.add(cliente)
            db.flush()

    now = datetime.now()
    total_venta = Decimal("0.00")
    detalles_orden = []

    for item in payload.items:
        stock = (
            db.query(StockInventario)
            .filter(StockInventario.id == item.stock_inventario_id)
            .with_for_update(of=StockInventario)
            .first()
        )
        if not stock:
            db.rollback()
            raise NotFoundException(f"Inventario #{item.stock_inventario_id} no encontrado.")

        if stock.cantidad < item.cantidad:
            db.rollback()
            raise BadRequestException(f"Stock insuficiente. Disponible: {stock.cantidad}, solicitado: {item.cantidad}.")

        stock.cantidad -= item.cantidad

        precio = Decimal("0.00")
        prod_nom = "Prenda"
        col_nom = None
        talla_nom = None
        if stock.producto_color:
            col_nom = stock.producto_color.color.nombre if stock.producto_color.color else None
            if stock.producto_color.producto:
                precio = stock.producto_color.producto.precio
                prod_nom = stock.producto_color.producto.nombre
        if stock.talla:
            talla_nom = stock.talla.nombre

        subtotal = precio * item.cantidad
        total_venta += subtotal

        detalles_orden.append({
            "stock_inventario_id": stock.id,
            "producto_nombre": prod_nom,
            "color_nombre": col_nom,
            "talla_nombre": talla_nom,
            "cantidad": item.cantidad,
            "precio_unitario": precio,
            "subtotal": subtotal,
        })

    # Cálculo de vuelto y validación de efectivo si aplica
    metodo = (payload.metodo_pago or "efectivo").lower()
    recibido = payload.efectivo_recibido or total_venta
    cambio = Decimal("0.00")
    if metodo == "efectivo" and recibido >= total_venta:
        cambio = recibido - total_venta

    ticket_num = f"TCK-{now.strftime('%Y%m%d%H%M%S')}"

    orden = OrdenVenta(
        fecha=now.date(),
        estado="pagada",
        total=total_venta,
        tipo_venta="presencial",
        metodo_pago=metodo,
        ticket_numero=ticket_num,
        efectivo_recibido=recibido if metodo == "efectivo" else total_venta,
        cambio_devuelto=cambio if metodo == "efectivo" else Decimal("0.00"),
        codigo_cliente=cliente.codigo,
        sucursal_id=payload.sucursal_id,
    )
    db.add(orden)
    db.flush()

    for d in detalles_orden:
        dv = DetalleVenta(
            orden_venta_id=orden.id,
            stock_inventario_id=d["stock_inventario_id"],
            producto_nombre=d["producto_nombre"],
            color_nombre=d["color_nombre"],
            talla_nombre=d["talla_nombre"],
            cantidad=d["cantidad"],
            precio_unitario=d["precio_unitario"],
            subtotal=d["subtotal"],
        )
        db.add(dv)

    pago = Pago(
        orden_venta_id=orden.id,
        monto=total_venta,
        tipo_pago="en caja",
        metodo_pago=metodo,
        estado="aprobado",
    )
    db.add(pago)

    db.commit()
    db.refresh(orden)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Registró venta presencial #{orden.id} ({ticket_num}) en caja por Bs {orden.total} [{metodo.upper()}] para cliente '{cliente.codigo}'",
        module="ventas",
    )

    return _serialize_orden(orden)


@router.delete("/{venta_id}", summary="Eliminar venta")
async def delete_venta(
    venta_id: int,
    current_user: User = Depends(require_permission("ventas.eliminar")),
    db: Session = Depends(get_db),
):
    """Eliminar un registro de orden de venta."""
    orden = db.query(OrdenVenta).filter(OrdenVenta.id == venta_id).first()
    if not orden:
        raise NotFoundException(f"Venta con ID {venta_id} no encontrada.")

    db.delete(orden)
    db.commit()

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Eliminó la venta #{venta_id}",
        module="ventas",
    )
    return {"message": f"Venta #{venta_id} eliminada exitosamente."}
