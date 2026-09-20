"""
Inventario endpoints (v5 sección 25).
Maneja inventario global consolidado e inventario por sucursal,
vinculando producto, color, talla, temporada y colección.
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User
from app.models.stock_inventario import StockInventario
from app.models.producto_color import ProductoColor
from app.models.producto import Producto
from app.api.deps import require_permission
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.bitacora_service import BitacoraService

router = APIRouter(prefix="/inventario", tags=["Inventario"])


class StockAdjustRequest(BaseModel):
    stock_inventario_id: int | None = None
    producto_color_id: int | None = None
    talla_id: int | None = None
    sucursal_id: int | None = None
    cantidad: int = Field(..., ge=0, description="Nueva cantidad de stock")


@router.get("/global", summary="Inventario Global Consolidado")
async def get_inventario_global(
    categoria_id: int | None = Query(None),
    temporada_id: int | None = Query(None),
    coleccion_id: int | None = Query(None),
    search: str | None = Query(None),
    current_user: User = Depends(require_permission("inventario.ver")),
    db: Session = Depends(get_db),
):
    """
    Vista de inventario global consolidado de todas las sucursales.
    Agrupa existencias por producto, color, talla, temporada y colección.
    """
    stocks = db.query(StockInventario).all()
    result = []
    for s in stocks:
        p_nom = None
        p_cod = None
        p_precio = None
        p_foto = None
        cat_nom = None
        temp_nom = None
        col_nom = None
        color_nom = None
        talla_nom = None
        suc_nom = None
        prod = None

        if s.producto_color:
            color_nom = s.producto_color.color.nombre if s.producto_color.color else None
            prod = s.producto_color.producto
            if prod:
                p_cod = prod.codigo
                p_nom = prod.nombre
                p_precio = float(prod.precio)
                p_foto = prod.foto
                cat_nom = prod.categoria.nombre if prod.categoria else None
                temp_nom = prod.temporada.nombre if prod.temporada else None
                col_nom = prod.coleccion.nombre if prod.coleccion else None

        if s.talla:
            talla_nom = s.talla.nombre
        if s.sucursal:
            name = getattr(s.sucursal, "name", getattr(s.sucursal, "nombre", ""))
            city = getattr(s.sucursal, "city", getattr(s.sucursal, "ciudad", ""))
            addr = getattr(s.sucursal, "address", getattr(s.sucursal, "direccion", ""))
            suc_nom = f"{name} ({city} - {addr})" if name and (city or addr) else (name or f"{city} - {addr}".strip(" -"))

        # Filtrado en memoria si aplica
        if search and search.lower() not in (p_nom or "").lower() and search.lower() not in (p_cod or "").lower():
            continue
        if categoria_id and (not prod or prod.categoria_id != categoria_id):
            continue
        if temporada_id and (not prod or prod.temporada_id != temporada_id):
            continue
        if coleccion_id and (not prod or prod.coleccion_id != coleccion_id):
            continue

        result.append({
            "stock_inventario_id": s.id,
            "producto_codigo": p_cod,
            "producto_nombre": p_nom,
            "foto": p_foto,
            "precio": p_precio,
            "categoria": cat_nom,
            "temporada": temp_nom,
            "coleccion": col_nom,
            "producto_color_id": s.producto_color_id,
            "color": color_nom,
            "talla_id": s.talla_id,
            "talla": talla_nom,
            "sucursal_id": s.sucursal_id,
            "sucursal": suc_nom,
            "cantidad": s.cantidad,
        })

    return result


@router.get("/sucursal/{sucursal_id}", summary="Inventario por Sucursal")
async def get_inventario_sucursal(
    sucursal_id: int,
    current_user: User = Depends(require_permission("inventario.ver")),
    db: Session = Depends(get_db),
):
    """Obtiene el inventario detallado para una sucursal específica."""
    stocks = db.query(StockInventario).filter(StockInventario.sucursal_id == sucursal_id).all()
    result = []
    for s in stocks:
        p_nom = None
        p_cod = None
        p_precio = None
        p_foto = None
        color_nom = None
        talla_nom = None
        suc_nom = None

        if s.producto_color:
            color_nom = s.producto_color.color.nombre if s.producto_color.color else None
            if s.producto_color.producto:
                p_cod = s.producto_color.producto.codigo
                p_nom = s.producto_color.producto.nombre
                p_precio = float(s.producto_color.producto.precio)
                p_foto = s.producto_color.producto.foto

        if s.talla:
            talla_nom = s.talla.nombre

        if s.sucursal:
            name = getattr(s.sucursal, "name", getattr(s.sucursal, "nombre", ""))
            city = getattr(s.sucursal, "city", getattr(s.sucursal, "ciudad", ""))
            addr = getattr(s.sucursal, "address", getattr(s.sucursal, "direccion", ""))
            suc_nom = f"{name} ({city} - {addr})" if name and (city or addr) else (name or f"{city} - {addr}".strip(" -"))

        result.append({
            "stock_inventario_id": s.id,
            "id": s.id,
            "producto_codigo": p_cod,
            "producto_nombre": p_nom,
            "foto": p_foto,
            "precio": p_precio,
            "precio_unitario": p_precio,
            "producto_color_id": s.producto_color_id,
            "color": color_nom,
            "color_nombre": color_nom,
            "talla_id": s.talla_id,
            "talla": talla_nom,
            "talla_nombre": talla_nom,
            "sucursal_id": s.sucursal_id,
            "sucursal": suc_nom,
            "cantidad": s.cantidad,
            "cantidad_disponible": s.cantidad,
        })
    return result



@router.post("/ajustar", summary="Ajustar o registrar stock de inventario")
async def ajustar_stock(
    payload: StockAdjustRequest,
    current_user: User = Depends(require_permission("inventario.editar")),
    db: Session = Depends(get_db),
):
    """Crea o actualiza la existencia de stock para una combinación producto-color-talla-sucursal."""
    stock = None
    if payload.stock_inventario_id:
        stock = db.query(StockInventario).filter(StockInventario.id == payload.stock_inventario_id).first()
        if not stock:
            raise NotFoundException("Registro de inventario no encontrado.")
        stock.cantidad = payload.cantidad
    elif payload.producto_color_id and payload.talla_id and payload.sucursal_id:
        stock = (
            db.query(StockInventario)
            .filter(
                StockInventario.producto_color_id == payload.producto_color_id,
                StockInventario.talla_id == payload.talla_id,
                StockInventario.sucursal_id == payload.sucursal_id,
            )
            .first()
        )
        if stock:
            stock.cantidad = payload.cantidad
        else:
            stock = StockInventario(
                producto_color_id=payload.producto_color_id,
                talla_id=payload.talla_id,
                sucursal_id=payload.sucursal_id,
                cantidad=payload.cantidad,
            )
            db.add(stock)
    else:
        raise BadRequestException("Debe proporcionar stock_inventario_id o la tupla (producto_color_id, talla_id, sucursal_id).")

    db.commit()
    db.refresh(stock)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Ajustó stock de inventario #{stock.id} a {stock.cantidad} unidades",
        module="inventario",
    )

    return {
        "message": "Stock actualizado exitosamente.",
        "stock_inventario_id": stock.id,
        "cantidad": stock.cantidad,
    }
