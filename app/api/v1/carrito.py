"""
Carrito endpoints (v5 sección 17 y 18).
Incluye carrito activo del cliente, confirmación con transacción de stock y generación de Orden de Venta.
"""
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, status, HTTPException
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
    CheckoutRequest,
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

        suc_id = None
        suc_nom = None
        suc_ciudad = None
        suc_dir = None
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
                suc_id = si.sucursal.id
                suc_nom = si.sucursal.nombre
                suc_ciudad = si.sucursal.ciudad
                suc_dir = si.sucursal.direccion

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
            "sucursal_id": suc_id,
            "sucursal_nombre": suc_nom,
            "sucursal_ciudad": suc_ciudad,
            "sucursal_direccion": suc_dir,
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
    if not carrito:
        raise NotFoundException("Carrito no encontrado.")
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
    if not carrito:
        raise NotFoundException("Carrito no encontrado.")
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
        sucursal_id_desde_stock = None

        # Validar y descontar stock atómicamente
        for item in carrito.items:
            stock = (
                db.query(StockInventario)
                .filter(StockInventario.id == item.stock_inventario_id)
                .with_for_update(of=StockInventario)
                .first()
            )
            if not stock:
                db.rollback()
                raise NotFoundException(f"Inventario para el ítem #{item.id} no encontrado.")

            if stock.cantidad < item.cantidad:
                db.rollback()
                prod_name = stock.producto_color.producto.nombre if (stock.producto_color and stock.producto_color.producto) else "Producto"
                raise BadRequestException(f"Stock insuficiente para '{prod_name}'. Disponible: {stock.cantidad}, requerido: {item.cantidad}.")

            if stock.sucursal_id and not sucursal_id_desde_stock:
                sucursal_id_desde_stock = stock.sucursal_id

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

        # La orden de venta se asocia directamente a la sucursal de donde procede el stock real de las prendas
        sucursal_final = sucursal_id_desde_stock or payload.sucursal_id
        if not sucursal_final:
            from app.models.sucursal import Sucursal
            first_suc = db.query(Sucursal).filter(Sucursal.active == True).first()
            if first_suc:
                sucursal_final = first_suc.id

        # Crear Orden de Venta
        metodo = (payload.metodo_pago or "EFECTIVO").upper()
        orden = OrdenVenta(
            fecha=now.date(),
            estado="pendiente_pago",
            total=total_venta,
            tipo_venta="en linea",
            codigo_cliente=cliente.codigo,
            sucursal_id=sucursal_final,
            carrito_id=carrito.id,
            metodo_pago=metodo,
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


@router.post("/checkout", summary="Checkout integral con Delivery StyleStore para Web y Móvil")
async def checkout_cart(
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Checkout integral para Web y Mobile:
    1. Confirma el carrito activo y descuenta stock atómicamente.
    2. Genera OrdenVenta y DetalleVenta.
    3. Si hay datos de entrega, crea el Envio con las coordenadas reales (casita) y token de tracking.
    """
    import uuid
    from app.models.envio import Envio
    from app.models.sucursal import Sucursal
    from app.core.geo import (
        extraer_coordenadas_de_url,
        geocodificar_aproximado,
        cotizar_costo_envio,
        calcular_distancia_haversine,
    )

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
        total_prendas = Decimal("0.00")
        detalles_orden = []
        sucursal_id_desde_stock = None

        for item in carrito.items:
            stock = (
                db.query(StockInventario)
                .filter(StockInventario.id == item.stock_inventario_id)
                .with_for_update(of=StockInventario)
                .first()
            )
            if not stock:
                db.rollback()
                raise NotFoundException(f"Inventario para el ítem #{item.id} no encontrado.")

            if stock.cantidad < item.cantidad:
                db.rollback()
                prod_name = stock.producto_color.producto.nombre if (stock.producto_color and stock.producto_color.producto) else "Producto"
                raise BadRequestException(f"Stock insuficiente para '{prod_name}'. Requerido: {item.cantidad}, Disponible: {stock.cantidad}")

            if stock.sucursal_id and not sucursal_id_desde_stock:
                sucursal_id_desde_stock = stock.sucursal_id

            stock.cantidad -= item.cantidad
            subtotal = item.precio_unitario * item.cantidad
            total_prendas += subtotal

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

        sucursal_final = sucursal_id_desde_stock or payload.sucursal_id
        if not sucursal_final:
            first_suc = db.query(Sucursal).filter(Sucursal.active == True).first()
            if first_suc:
                sucursal_final = first_suc.id

        metodo = (payload.metodo_pago or "EFECTIVO").upper()
        orden = OrdenVenta(
            fecha=now.date(),
            estado="pendiente_pago",
            total=total_prendas,
            tipo_venta="en linea",
            codigo_cliente=cliente.codigo,
            sucursal_id=sucursal_final,
            carrito_id=carrito.id,
            metodo_pago=metodo,
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

        # Procesar despacho con Delivery StyleStore si se especificó dirección o distancia
        token_seg = None
        costo_envio = Decimal("0.00")
        envio_creado = None

        tiene_despacho = bool(payload.direccion_envio or payload.ubicacion_url or payload.distancia_km)
        if tiene_despacho:
            ub_url = payload.ubicacion_url.strip() if payload.ubicacion_url else None
            dir_env = payload.direccion_envio.strip() if payload.direccion_envio else (ub_url or "Entrega a domicilio")

            dest_lat = payload.latitud_destino
            dest_lon = payload.longitud_destino

            if dest_lat is None or dest_lon is None:
                if ub_url:
                    dest_lat, dest_lon = extraer_coordenadas_de_url(ub_url)
                elif dir_env:
                    dest_lat, dest_lon = extraer_coordenadas_de_url(dir_env)

            if dest_lat is None or dest_lon is None:
                texto_busqueda = f"{dir_env} {payload.referencia or ''} {payload.ciudad or ''}"
                dest_lat, dest_lon = geocodificar_aproximado(texto_busqueda)

            # Sucursal origen
            suc = db.query(Sucursal).filter(Sucursal.id == sucursal_final).first()
            orig_lat = float(suc.latitud) if (suc and suc.latitud) else None
            orig_lon = float(suc.longitud) if (suc and suc.longitud) else None
            if (orig_lat is None or orig_lon is None) and suc and suc.maps_url:
                orig_lat, orig_lon = extraer_coordenadas_de_url(suc.maps_url)
            if orig_lat is None or orig_lon is None:
                orig_lat, orig_lon = geocodificar_aproximado(suc.ciudad if suc else (payload.ciudad or "Santa Cruz"))

            dist_calc = payload.distancia_km
            if dist_calc is None and dest_lat is not None and dest_lon is not None and orig_lat is not None and orig_lon is not None:
                dist_calc = calcular_distancia_haversine(orig_lat, orig_lon, dest_lat, dest_lon)
            if dist_calc is None:
                dist_calc = 3.5

            costo_envio = cotizar_costo_envio(dist_calc)
            orden.total = total_prendas + costo_envio

            token_seg = f"TRK-{uuid.uuid4().hex[:10].upper()}"
            envio_creado = Envio(
                orden_venta_id=orden.id,
                direccion=dir_env,
                ciudad=payload.ciudad.strip() if payload.ciudad else (suc.ciudad if suc else "Santa Cruz"),
                referencia=payload.referencia.strip() if payload.referencia else None,
                ubicacion_url=ub_url or (f"https://www.google.com/maps?q={dest_lat},{dest_lon}" if dest_lat and dest_lon else None),
                latitud_destino=Decimal(str(round(dest_lat, 6))) if dest_lat is not None else None,
                longitud_destino=Decimal(str(round(dest_lon, 6))) if dest_lon is not None else None,
                distancia_km=Decimal(str(round(dist_calc, 2))),
                minutos_estimados=max(15, int(dist_calc * 2.5) + 15),
                costo=costo_envio,
                estado="pendiente",
                fecha=now.date(),
                token_seguimiento=token_seg,
                tracking_activo=True,
                delivery_conductor="Repartidor StyleStore",
            )
            db.add(envio_creado)

        db.commit()
        db.refresh(orden)

        try:
            BitacoraService.registrar(
                db=db,
                user=current_user,
                action=f"Checkout exitoso de Orden #{orden.id} (Total: Bs {orden.total}, Delivery: Bs {costo_envio})",
                module="carrito",
            )
        except Exception:
            pass

        return {
            "message": "Pedido confirmado exitosamente.",
            "orden_venta_id": orden.id,
            "total": float(orden.total),
            "estado": orden.estado,
            "costo_envio": float(costo_envio),
            "token_seguimiento": token_seg,
            "tracking_url": f"/delivery/rastreo/{token_seg}" if token_seg else None,
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
            detail=f"Error al procesar el checkout: {str(e)}",
        )


@router.get("", summary="Listado administrativo de carritos")
async def list_admin_carritos(
    current_user: User = Depends(require_permission("carrito.ver")),
    db: Session = Depends(get_db),
):
    """Listado de compras por carrito para vista administrativa."""
    carritos = db.query(Carrito).order_by(Carrito.created_at.desc()).all()
    return [_serialize_carrito(c) for c in carritos]
