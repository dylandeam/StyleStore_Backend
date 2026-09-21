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
                    "sucursal_nombre": s.sucursal.nombre if s.sucursal else None,
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

        if sucursal_id is not None and stock_total <= 0:
            continue

        result.append({
            "codigo": p.codigo,
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "foto": p.foto,
            "foto_trasera": getattr(p, "foto_trasera", None),
            "foto_vestidor_frontal": getattr(p, "foto_vestidor_frontal", None),
            "foto_vestidor_trasera": getattr(p, "foto_vestidor_trasera", None),
            "tipo_prenda": getattr(p, "tipo_prenda", "superior") or "superior",
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


from app.core.exceptions import NotFoundException
from app.services.recommendation_service import RecommendationService
from app.api.deps import get_optional_current_user
from app.models.user import User


@router.get("/para-ti", summary="Feed de recomendaciones inteligentes Para Ti con IA local")
async def get_catalogo_para_ti(
    limit: int = Query(6, ge=1, le=12),
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Feed 'Para Ti' con IA Local: personaliza recomendaciones afines basadas
    en el perfil del cliente o sugiere prendas de alta afinidad de colección.
    """
    service = RecommendationService(db)
    user_id = current_user.id if current_user else None
    return service.get_para_ti_recommendations(user_id=user_id, limit=limit)


@router.get("/{codigo}/detalle", summary="Obtener detalle completo de un producto para compra")
async def get_producto_detalle(
    codigo: str,
    sucursal_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """
    Obtiene la ficha técnica y comercial del producto con todas sus variantes de color,
    tallas asociadas y existencias de stock disponibles para venta directa o carrito.
    Permite filtrar existencias por sucursal específica.
    """
    # Búsqueda insensible a mayúsculas/minúsculas y espacios
    clean_cod = codigo.strip().lower()
    p = db.query(Producto).filter(func.lower(Producto.codigo) == clean_cod).first()
    if not p:
        raise NotFoundException(f"Producto con código '{codigo}' no encontrado.")

    variantes = []
    stock_total = 0

    if p.colores_rel:
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
                    "sucursal_nombre": s.sucursal.nombre if s.sucursal else None,
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

    # Si no tiene variantes de color asociadas, agregamos una variante estándar
    if not variantes:
        variantes.append({
            "producto_color_id": 0,
            "color_id": 0,
            "color_nombre": "Único",
            "color_hex": "#14263D",
            "existencias": [],
        })

    return {
        "codigo": p.codigo,
        "nombre": p.nombre,
        "descripcion": p.descripcion,
        "foto": p.foto,
        "foto_trasera": getattr(p, "foto_trasera", None),
        "foto_vestidor_frontal": getattr(p, "foto_vestidor_frontal", None),
        "foto_vestidor_trasera": getattr(p, "foto_vestidor_trasera", None),
        "tipo_prenda": getattr(p, "tipo_prenda", "superior") or "superior",
        "precio": float(p.precio),
        "categoria_id": p.categoria_id,
        "categoria_nombre": p.categoria.nombre if p.categoria else None,
        "temporada_id": p.temporada_id,
        "temporada_nombre": p.temporada.nombre if p.temporada else None,
        "coleccion_id": p.coleccion_id,
        "coleccion_nombre": p.coleccion.nombre if p.coleccion else None,
        "variantes": variantes,
        "stock_total": stock_total,
    }


@router.get("/{codigo}/recomendados", summary="Recomendaciones de IA local para un producto")
async def get_producto_recomendados(
    codigo: str,
    limit: int = Query(4, ge=1, le=12),
    db: Session = Depends(get_db),
):
    """
    Analiza las características del producto y genera sugerencias afines mediante
    el motor de IA local de StyleStore.
    """
    service = RecommendationService(db)
    return service.get_recommendations_for_product(codigo=codigo, limit=limit)

