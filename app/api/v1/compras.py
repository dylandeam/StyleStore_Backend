"""
Endpoints para el Módulo de Compras a Proveedores (Punto 2 / v7).
Permite registrar compras a proveedores, abastecer automáticamente inventario por sucursal,
consultar bitácora y anular compras con reversión de existencias.
"""
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.proveedor import Proveedor
from app.models.sucursal import Sucursal
from app.models.producto import Producto
from app.models.color import Color
from app.models.talla import Talla
from app.models.producto_color import ProductoColor
from app.models.stock_inventario import StockInventario
from app.models.compra import Compra, DetalleCompra
from app.schemas.compra import CompraCreate, CompraResponse, DetalleCompraResponse
from app.api.deps import get_current_user
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.bitacora_service import BitacoraService

router = APIRouter(prefix="/compras", tags=["Compras a Proveedores"])


def _formatear_compra(c: Compra) -> CompraResponse:
    detalles_resp = []
    for d in c.detalles:
        detalles_resp.append(
            DetalleCompraResponse(
                id=d.id,
                producto_codigo=d.producto_codigo,
                producto_nombre=d.producto.nombre if d.producto else d.producto_codigo,
                color_id=d.color_id,
                color_nombre=d.color.nombre if d.color else str(d.color_id),
                talla_id=d.talla_id,
                talla_nombre=d.talla.nombre if d.talla else str(d.talla_id),
                cantidad=d.cantidad,
                costo_unitario=d.costo_unitario,
                subtotal=d.subtotal,
            )
        )

    return CompraResponse(
        id=c.id,
        fecha=c.fecha,
        proveedor_codigo=c.proveedor_codigo,
        proveedor_nombre=c.proveedor.nombre if c.proveedor else None,
        sucursal_id=c.sucursal_id,
        sucursal_nombre=f"{c.sucursal.nombre} ({c.sucursal.ciudad})" if c.sucursal else None,
        nro_factura=c.nro_factura,
        total=c.total,
        estado=c.estado,
        observaciones=c.observaciones,
        created_at=c.created_at,
        detalles=detalles_resp,
    )


@router.get("", response_model=list[CompraResponse], summary="Listar compras a proveedores")
async def list_compras(
    sucursal_id: int | None = Query(None, description="Filtrar por sucursal"),
    proveedor_codigo: str | None = Query(None, description="Filtrar por proveedor"),
    estado: str | None = Query(None, description="Filtrar por estado: registrada o anulada"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna listado de compras realizadas a proveedores."""
    q = db.query(Compra)
    if sucursal_id:
        q = q.filter(Compra.sucursal_id == sucursal_id)
    if proveedor_codigo:
        q = q.filter(Compra.proveedor_codigo == proveedor_codigo)
    if estado:
        q = q.filter(Compra.estado == estado)

    compras = q.order_by(Compra.created_at.desc()).all()
    return [_formatear_compra(c) for c in compras]


@router.get("/{compra_id}", response_model=CompraResponse, summary="Obtener detalle de compra")
async def get_compra(
    compra_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve el detalle de una compra específica con todos sus productos."""
    compra = db.query(Compra).filter(Compra.id == compra_id).first()
    if not compra:
        raise NotFoundException(f"Compra con ID {compra_id} no encontrada.")
    return _formatear_compra(compra)


@router.post("", response_model=CompraResponse, status_code=status.HTTP_201_CREATED, summary="Registrar nueva compra y abastecer inventario")
async def create_compra(
    payload: CompraCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Registra una nueva compra a proveedor y actualiza automáticamente
    el stock en la sucursal de destino seleccionada (Stock_Inventario).
    """
    proveedor = db.query(Proveedor).filter(Proveedor.codigo == payload.proveedor_codigo).first()
    if not proveedor:
        raise NotFoundException(f"Proveedor con código '{payload.proveedor_codigo}' no encontrado.")

    sucursal = db.query(Sucursal).filter(Sucursal.id == payload.sucursal_id).first()
    if not sucursal:
        raise NotFoundException(f"Sucursal de destino con ID {payload.sucursal_id} no encontrada.")

    total_calculado = Decimal("0.00")

    compra = Compra(
        proveedor_codigo=payload.proveedor_codigo,
        sucursal_id=payload.sucursal_id,
        nro_factura=payload.nro_factura.strip() if payload.nro_factura else None,
        observaciones=payload.observaciones.strip() if payload.observaciones else None,
        total=Decimal("0.00"),
        estado="registrada",
    )
    db.add(compra)
    db.flush()

    for item in payload.items:
        prod = db.query(Producto).filter(Producto.codigo == item.producto_codigo).first()
        if not prod:
            raise NotFoundException(f"Producto con código '{item.producto_codigo}' no existe.")

        color = db.query(Color).filter(Color.id == item.color_id).first()
        if not color:
            raise NotFoundException(f"Color con ID {item.color_id} no existe.")

        talla = db.query(Talla).filter(Talla.id == item.talla_id).first()
        if not talla:
            raise NotFoundException(f"Talla con ID {item.talla_id} no existe.")

        subtotal_item = Decimal(str(item.costo_unitario)) * item.cantidad
        total_calculado += subtotal_item

        det = DetalleCompra(
            compra_id=compra.id,
            producto_codigo=item.producto_codigo,
            color_id=item.color_id,
            talla_id=item.talla_id,
            cantidad=item.cantidad,
            costo_unitario=Decimal(str(item.costo_unitario)),
            subtotal=subtotal_item,
        )
        db.add(det)

        # -------------------------------------------------------------
        # ABASTECIMIENTO DE STOCK EN SUCURSAL DESTINO
        # -------------------------------------------------------------
        pc = db.query(ProductoColor).filter(
            ProductoColor.producto_codigo == item.producto_codigo,
            ProductoColor.color_id == item.color_id,
        ).first()

        if not pc:
            pc = ProductoColor(
                producto_codigo=item.producto_codigo,
                color_id=item.color_id,
            )
            db.add(pc)
            db.flush()

        stk = db.query(StockInventario).filter(
            StockInventario.producto_color_id == pc.id,
            StockInventario.talla_id == item.talla_id,
            StockInventario.sucursal_id == payload.sucursal_id,
        ).first()

        if not stk:
            stk = StockInventario(
                producto_color_id=pc.id,
                talla_id=item.talla_id,
                sucursal_id=payload.sucursal_id,
                cantidad=item.cantidad,
            )
            db.add(stk)
        else:
            stk.cantidad += item.cantidad

    compra.total = total_calculado
    db.commit()
    db.refresh(compra)

    # Registrar en Bitácora
    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Registró compra #{compra.id} a proveedor '{proveedor.nombre}' por Bs. {compra.total:.2f}. Abastecidas {len(payload.items)} prendas a sucursal '{sucursal.nombre}'",
        module="compras",
    )

    return _formatear_compra(compra)


@router.post("/{compra_id}/anular", response_model=CompraResponse, summary="Anular compra y revertir stock")
async def anular_compra(
    compra_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Anula una compra registrada previamente y descuenta el stock que se había
    incorporado a la sucursal de destino.
    """
    compra = db.query(Compra).filter(Compra.id == compra_id).first()
    if not compra:
        raise NotFoundException(f"Compra con ID {compra_id} no encontrada.")

    if compra.estado == "anulada":
        raise BadRequestException("La compra ya se encuentra anulada.")

    # Revertir stock de cada detalle
    for d in compra.detalles:
        pc = db.query(ProductoColor).filter(
            ProductoColor.producto_codigo == d.producto_codigo,
            ProductoColor.color_id == d.color_id,
        ).first()

        if pc:
            stk = db.query(StockInventario).filter(
                StockInventario.producto_color_id == pc.id,
                StockInventario.talla_id == d.talla_id,
                StockInventario.sucursal_id == compra.sucursal_id,
            ).first()

            if stk:
                stk.cantidad = max(0, stk.cantidad - d.cantidad)

    compra.estado = "anulada"
    db.commit()
    db.refresh(compra)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Anuló compra #{compra.id} y revirtió el stock ingresado a la sucursal '{compra.sucursal.nombre if compra.sucursal else compra.sucursal_id}'",
        module="compras",
    )

    return _formatear_compra(compra)
