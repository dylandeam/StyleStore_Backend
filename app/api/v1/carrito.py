"""
Carrito endpoints (v5 sección 17 y 18).
Incluye carrito activo del cliente, confirmación con transacción de stock y generación de Orden de Venta.
"""
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.cliente import Cliente
from app.models.carrito import Carrito, DetalleCarrito
from app.models.stock_inventario import StockInventario
from app.models.orden_venta import OrdenVenta, DetalleVenta
from app.schemas.carrito import (
    CarritoResponse,
    DetalleCarritoCreate,
    DetalleCarritoUpdate,
    ConfirmarCarritoRequest,
)
from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.bitacora_service import BitacoraService

router = APIRouter(prefix="/carrito", tags=["Carrito de Compras"])


def _get_or_create_cliente(user: User, db: Session) -> Cliente:
    cli = db.query(Cliente).filter(Cliente.user_id == user.id).first()
    if not cli:
        clean_ci = user.ci or str(user.id).zfill(4)
        cod = f"CL-{user.name[:2].upper()}-{clean_ci[-4:]}"
        existing_cod = db.query(Cliente).filter(Cliente.codigo == cod).first()
        if existing_cod:
            cod = f"CL-{user.name[:2].upper()}-{user.id}"
        cli = Cliente(
            codigo=cod,
            user_id=user.id,
            telefono=user.telefono or "00000000",
            direccion=user.direccion or "Sin dirección",
        )
        db.add(cli)
        db.commit()
        db.refresh(cli)
    return cli


def _serialize_carrito(carrito: Carrito) -> dict:
    items_resp = []
    total = Decimal("0.00")
    for it in carrito.items:
        si = it.stock_inventario
        sub = it.precio_unitario * it.cantidad
        total += sub

        prod_cod = None
        prod_nom = None
        col_nom = None
        talla_nom = None
        suc_nom = None
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
            if si.sucursal:
                suc_nom = f"{si.sucursal.ciudad} - {si.sucursal.direccion}"

        items_resp.append({
            "id": it.id,
            "stock_inventario_id": it.stock_inventario_id,
            "cantidad": it.cantidad,
            "precio_unitario": it.precio_unitario,
            "subtotal": sub,
            "producto_codigo": prod_cod,
            "producto_nombre": prod_nom,
            "color_nombre": col_nom,
            "talla_nombre": talla_nom,
            "sucursal_nombre": suc_nom,
            "foto": foto,
        })

    return {
        "id": carrito.id,
        "fecha": carrito.fecha,
        "estado": carrito.estado,
        "codigo_cliente": carrito.codigo_cliente,
        "items": items_resp,
        "total": total,
        "created_at": carrito.created_at,
    }


@router.get("/mio", response_model=CarritoResponse, summary="Obtener carrito activo del cliente")
async def get_my_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene o inicializa el carrito activo para el cliente en sesión."""
    cliente = _get_or_create_cliente(current_user, db)
    carrito = (
        db.query(Carrito)
        .filter(Carrito.codigo_cliente == cliente.codigo, Carrito.estado == "activo")
        .first()
    )
    if not carrito:
        carrito = Carrito(
            fecha=datetime.now().date(),
            estado="activo",
            codigo_cliente=cliente.codigo,
        )
        db.add(carrito)
        db.commit()
        db.refresh(carrito)

    return _serialize_carrito(carrito)


@router.post("/items", response_model=CarritoResponse, summary="Agregar producto al carrito")
async def add_item_to_cart(
    payload: DetalleCarritoCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Agrega un producto/talla/color al carrito activo."""
    cliente = _get_or_create_cliente(current_user, db)
    carrito = (
        db.query(Carrito)
        .filter(Carrito.codigo_cliente == cliente.codigo, Carrito.estado == "activo")
        .first()
    )
    if not carrito:
        carrito = Carrito(
            fecha=datetime.now().date(),
            estado="activo",
            codigo_cliente=cliente.codigo,
        )
        db.add(carrito)
        db.flush()

    stock = db.query(StockInventario).filter(StockInventario.id == payload.stock_inventario_id).first()
    if not stock:
        raise NotFoundException(f"Inventario con ID {payload.stock_inventario_id} no encontrado.")

    # Obtener precio del producto
    precio = Decimal("0.00")
    if stock.producto_color and stock.producto_color.producto:
        precio = stock.producto_color.producto.precio

    # Validar si ya existe en el carrito
    existing_item = (
        db.query(DetalleCarrito)
        .filter(
            DetalleCarrito.carrito_id == carrito.id,
            DetalleCarrito.stock_inventario_id == stock.id,
        )
        .first()
    )

    if existing_item:
        new_cant = existing_item.cantidad + payload.cantidad
        if stock.cantidad < new_cant:
            raise BadRequestException(f"Stock insuficiente. Disponible: {stock.cantidad}, en carrito: {new_cant}.")
        existing_item.cantidad = new_cant
    else:
        if stock.cantidad < payload.cantidad:
            raise BadRequestException(f"Stock insuficiente. Disponible: {stock.cantidad}, solicitado: {payload.cantidad}.")
        item = DetalleCarrito(
            carrito_id=carrito.id,
            stock_inventario_id=stock.id,
            cantidad=payload.cantidad,
            precio_unitario=precio,
        )
        db.add(item)

    db.commit()
    db.refresh(carrito)
    return _serialize_carrito(carrito)


@router.patch("/items/{item_id}", response_model=CarritoResponse, summary="Actualizar cantidad de un ítem")
async def update_cart_item(
    item_id: int,
    payload: DetalleCarritoUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Actualiza la cantidad de un ítem del carrito (si es 0, lo quita)."""
    cliente = _get_or_create_cliente(current_user, db)
    item = (
        db.query(DetalleCarrito)
        .join(Carrito, DetalleCarrito.carrito_id == Carrito.id)
        .filter(DetalleCarrito.id == item_id, Carrito.codigo_cliente == cliente.codigo, Carrito.estado == "activo")
        .first()
    )
    if not item:
        raise NotFoundException(f"Ítem con ID {item_id} no encontrado en tu carrito activo.")

    if payload.cantidad <= 0:
        db.delete(item)
    else:
        stock = db.query(StockInventario).filter(StockInventario.id == item.stock_inventario_id).first()
        if stock and stock.cantidad < payload.cantidad:
            raise BadRequestException(f"Stock insuficiente. Disponible: {stock.cantidad}.")
        item.cantidad = payload.cantidad

    db.commit()
    carrito = db.query(Carrito).filter(Carrito.id == item.carrito_id).first()
    return _serialize_carrito(carrito)


@router.delete("/items/{item_id}", response_model=CarritoResponse, summary="Quitar ítem del carrito")
async def remove_cart_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Quita un producto del carrito activo."""
    cliente = _get_or_create_cliente(current_user, db)
    item = (
        db.query(DetalleCarrito)
        .join(Carrito, DetalleCarrito.carrito_id == Carrito.id)
        .filter(DetalleCarrito.id == item_id, Carrito.codigo_cliente == cliente.codigo, Carrito.estado == "activo")
        .first()
    )
    if not item:
        raise NotFoundException(f"Ítem con ID {item_id} no encontrado en tu carrito activo.")

    carrito_id = item.carrito_id
    db.delete(item)
    db.commit()

    carrito = db.query(Carrito).filter(Carrito.id == carrito_id).first()
    return _serialize_carrito(carrito)


@router.post("/confirmar", summary="Confirmar carrito y generar Orden de Venta")
async def confirm_cart(
    payload: ConfirmarCarritoRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Confirma el carrito:
    1. Descuenta automáticamente el stock dentro de una transacción.
    2. Cambia estado del carrito a 'confirmado'.
    3. Genera automáticamente la Orden de Venta y Detalle_Venta.
    """
    try:
        cliente = _get_or_create_cliente(current_user, db)
        carrito = (
            db.query(Carrito)
            .filter(Carrito.codigo_cliente == cliente.codigo, Carrito.estado == "activo")
            .first()
        )
        if not carrito or not carrito.items:
            raise BadRequestException("El carrito está vacío o ya fue confirmado.")

        now = datetime.now()
        total_venta = Decimal("0.00")
        detalles_orden = []
        sucursal_id = payload.sucursal_id

        # Validar y descontar stock atómicamente
        for item in carrito.items:
            stock = db.query(StockInventario).filter(StockInventario.id == item.stock_inventario_id).with_for_update().first()
            if not stock:
                db.rollback()
                raise NotFoundException(f"Inventario para el ítem #{item.id} no encontrado.")

            if stock.cantidad < item.cantidad:
                db.rollback()
                prod_name = stock.producto_color.producto.nombre if (stock.producto_color and stock.producto_color.producto) else "Producto"
                raise BadRequestException(f"Stock insuficiente para '{prod_name}'. Disponible: {stock.cantidad}, requerido: {item.cantidad}.")

            # Si no se pasó sucursal_id explícita, adoptar la sucursal de donde proviene el stock
            if not sucursal_id and stock.sucursal_id:
                sucursal_id = stock.sucursal_id

            # Descuento atómico
            stock.cantidad -= item.cantidad

            # Datos para detalle venta
            subtotal = item.precio_unitario * item.cantidad
            total_venta += subtotal

            prod_nom = "Prenda"
            col_nom = None
            talla_nom = None
            if stock.producto_color:
                col_nom = stock.producto_color.color.nombre if stock.producto_color.color else None
                if stock.producto_color.producto:
                    prod_nom = stock.producto_color.producto.nombre
            if stock.talla:
                talla_nom = stock.talla.nombre

            detalles_orden.append({
                "stock_inventario_id": stock.id,
                "producto_nombre": prod_nom,
                "color_nombre": col_nom,
                "talla_nombre": talla_nom,
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario,
                "subtotal": subtotal,
            })

        # Si aún no hay sucursal_id, buscar la primera sucursal activa como fallback seguro
        if not sucursal_id:
            from app.models.sucursal import Sucursal
            first_suc = db.query(Sucursal).filter(Sucursal.active == True).first()
            if first_suc:
                sucursal_id = first_suc.id

        # Crear Orden de Venta
        orden = OrdenVenta(
            fecha=now.date(),
            estado="pendiente_pago",
            total=total_venta,
            tipo_venta="en linea",
            codigo_cliente=cliente.codigo,
            sucursal_id=sucursal_id,
            carrito_id=carrito.id,
            metodo_pago="EFECTIVO",
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

        carrito.estado = "confirmado"
        db.commit()
        db.refresh(orden)

        try:
            BitacoraService.registrar(
                db=db,
                user=current_user,
                action=f"Confirmó carrito #{carrito.id} generando Orden de Venta #{orden.id} por Bs {orden.total}",
                module="carrito",
            )
        except Exception as b_err:
            print(f"Warning bitacora registro: {b_err}")

        return {
            "message": "Carrito confirmado exitosamente.",
            "orden_venta_id": orden.id,
            "total": orden.total,
            "estado": orden.estado,
        }
    except (BadRequestException, NotFoundException, HTTPException):
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=400,
            detail=f"Error al procesar la orden: {str(e)}",
        )


@router.get("", summary="Listado administrativo de carritos")
async def list_admin_carritos(
    current_user: User = Depends(require_permission("carrito.ver")),
    db: Session = Depends(get_db),
):
    """Listado de compras por carrito para vista administrativa."""
    carritos = db.query(Carrito).order_by(Carrito.created_at.desc()).all()
    return [_serialize_carrito(c) for c in carritos]
