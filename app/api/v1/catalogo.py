"""
Catálogo interactivo endpoints (v5 sección 15).
Muestra productos visibles en catálogo con colores, tallas y stock disponible en tiempo real.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.producto import Producto
from app.models.stock_inventario import StockInventario
from app.models.producto_color import ProductoColor
from app.models.color import Color
from app.models.talla import Talla
from app.models.sucursal import Sucursal

router = APIRouter(prefix="/catalogo", tags=["Catálogo"])


@router.get("", summary="Listar catálogo interactivo de productos")
async def get_catalogo(
    categoria_id: int | None = Query(None),
    temporada_id: int | None = Query(None),
    coleccion_id: int | None = Query(None),
    sucursal_id: int | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """
    Obtiene los productos activos visibles en catálogo,
    incluyendo variantes de color, tallas disponibles y stock por sucursal.
    """
    query = db.query(Producto).filter(Producto.active.is_(True), Producto.visible_en_catalogo.is_(True))

    if categoria_id:
        query = query.filter(Producto.categoria_id == categoria_id)
    if temporada_id:
        query = query.filter(Producto.temporada_id == temporada_id)
    if coleccion_id:
        query = query.filter(Producto.coleccion_id == coleccion_id)
    if search:
        query = query.filter(
            (Producto.nombre.ilike(f"%{search}%")) | (Producto.descripcion.ilike(f"%{search}%"))
        )

    prods = query.order_by(Producto.nombre.asc()).all()
    result = []

    for p in prods:
        # Extraer variantes de color y stock
        variantes = []
        stock_total = 0

        for pc in p.colores_rel:
            stock_query = db.query(StockInventario).filter(StockInventario.producto_color_id == pc.id)
            if sucursal_id:
                stock_query = stock_query.filter(StockInventario.sucursal_id == sucursal_id)

            stocks = stock_query.all()
            tallas_stock = []
            for s in stocks:
                stock_total += s.cantidad
                tallas_stock.append({
                    "stock_inventario_id": s.id,
                    "talla_id": s.talla_id,
                    "talla_nombre": s.talla.nombre if s.talla else None,
                    "sucursal_id": s.sucursal_id,
                    "sucursal_ciudad": s.sucursal.ciudad if s.sucursal else None,
                    "cantidad": s.cantidad,
                })

            if pc.color:
                variantes.append({
                    "producto_color_id": pc.id,
                    "color_id": pc.color.id,
                    "color_nombre": pc.color.nombre,
                    "color_hex": getattr(pc.color, "codigo_hex", None) or getattr(pc.color, "hex", None),
                    "existencias": tallas_stock,
                })

        result.append({
            "codigo": p.codigo,
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "foto": p.foto,
            "precio": float(p.precio),
            "categoria_id": p.categoria_id,
            "categoria_nombre": p.categoria.nombre if p.categoria else None,
            "temporada_id": p.temporada_id,
            "temporada_nombre": p.temporada.nombre if p.temporada else None,
            "coleccion_id": p.coleccion_id,
            "coleccion_nombre": p.coleccion.nombre if p.coleccion else None,
            "variantes": variantes,
            "stock_total": stock_total,
        })

    return result
