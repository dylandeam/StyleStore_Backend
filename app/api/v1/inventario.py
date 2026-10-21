"""
Inventario endpoints (v5 sección 25).
Maneja inventario global consolidado e inventario por sucursal,
vinculando producto, color, talla, temporada y colección.
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.database import get_db
from app.models.user import User
from app.models.stock_inventario import StockInventario
from app.models.producto_color import ProductoColor
from app.models.producto import Producto
from app.models.talla import Talla
from app.api.deps import require_permission, require_plan_capability
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.bitacora_service import BitacoraService
from app.services.tenant_scope import get_scoped_sucursal, scope_by_empresa, scope_by_sucursal
from app.schemas.traspaso_inventario import (
    TraspasoCreateRequest,
    TraspasoDecisionRequest,
    TraspasoResponse,
)
from app.services.traspaso_inventario_service import TraspasoInventarioService
from app.services.promocion_service import PromocionService

router = APIRouter(prefix="/inventario", tags=["Inventario"])


@router.get("/traspasos", response_model=list[TraspasoResponse], summary="Listar traspasos del tenant")
async def listar_traspasos(
    estado: str | None = Query(None, pattern="^(pendiente|aprobado|rechazado|cancelado)$"),
    current_user: User = Depends(require_permission("inventario.ver")),
    db: Session = Depends(get_db),
):
    service = TraspasoInventarioService(db)
    return [service.serialize(item) for item in service.list(current_user, estado)]


@router.post(
    "/traspasos",
    response_model=TraspasoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Solicitar un traspaso entre sucursales",
    dependencies=[Depends(require_plan_capability("productos"))],
)
async def crear_traspaso(
    payload: TraspasoCreateRequest,
    current_user: User = Depends(require_permission("inventario.editar")),
    db: Session = Depends(get_db),
):
    service = TraspasoInventarioService(db)
    return service.serialize(service.create(payload, current_user))


@router.post("/traspasos/{traspaso_id}/aprobar", response_model=TraspasoResponse)
async def aprobar_traspaso(
    traspaso_id: int,
    payload: TraspasoDecisionRequest,
    current_user: User = Depends(require_permission("inventario.editar")),
    db: Session = Depends(get_db),
):
    service = TraspasoInventarioService(db)
    return service.serialize(service.approve(traspaso_id, payload.respuesta, current_user))


@router.post("/traspasos/{traspaso_id}/rechazar", response_model=TraspasoResponse)
async def rechazar_traspaso(
    traspaso_id: int,
    payload: TraspasoDecisionRequest,
    current_user: User = Depends(require_permission("inventario.editar")),
    db: Session = Depends(get_db),
):
    service = TraspasoInventarioService(db)
    return service.serialize(
        service.decide_without_movement(traspaso_id, "rechazado", payload.respuesta, current_user)
    )


@router.post("/traspasos/{traspaso_id}/cancelar", response_model=TraspasoResponse)
async def cancelar_traspaso(
    traspaso_id: int,
    payload: TraspasoDecisionRequest,
    current_user: User = Depends(require_permission("inventario.editar")),
    db: Session = Depends(get_db),
):
    service = TraspasoInventarioService(db)
    return service.serialize(
        service.decide_without_movement(traspaso_id, "cancelado", payload.respuesta, current_user)
    )


class StockAdjustRequest(BaseModel):
    stock_inventario_id: int | None = None
    producto_color_id: int | None = None
    talla_id: int | None = None
    sucursal_id: int | None = None
    cantidad: int = Field(..., ge=0, description="Nueva cantidad de stock")
    precio_variante: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    medidas: dict[str, float] | None = None

    @field_validator("medidas")
    @classmethod
    def validate_measurements(cls, value: dict[str, float] | None):
        if value is None:
            return value
        if len(value) > 20:
            raise ValueError("Solo se permiten hasta 20 medidas por variante.")
        cleaned: dict[str, float] = {}
        for key, measure in value.items():
            name = key.strip().lower().replace(" ", "_")
            if not name or len(name) > 40 or measure <= 0 or measure > 1000:
                raise ValueError("Las medidas deben tener nombre y un valor entre 0 y 1000 cm.")
            cleaned[name] = round(float(measure), 2)
        return cleaned


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
    stocks_query = scope_by_sucursal(
        db.query(StockInventario), db, current_user, StockInventario.sucursal_id
    )
    stocks = stocks_query.all()
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
                _, precio_promocional, porcentaje_promocion = PromocionService(db).precio_stock(s)
                p_precio = float(precio_promocional)
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
            "porcentaje_promocion": porcentaje_promocion if prod else 0,
            "precio_variante": float(s.precio_variante) if s.precio_variante is not None else None,
            "medidas": s.medidas or {},
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
    get_scoped_sucursal(db, current_user, sucursal_id)
    stocks = db.query(StockInventario).filter(StockInventario.sucursal_id == sucursal_id).all()
    result = []
    for s in stocks:
        p_nom = None
        p_cod = None
        p_precio = None
        p_foto = None
        p_cat_nom = None
        p_cat_id = None
        color_nom = None
        talla_nom = None
        suc_nom = None

        if s.producto_color:
            color_nom = s.producto_color.color.nombre if s.producto_color.color else None
            if s.producto_color.producto:
                p_cod = s.producto_color.producto.codigo
                p_nom = s.producto_color.producto.nombre
                precio_original, precio_promocional, porcentaje_promocion = PromocionService(db).precio_stock(s)
                p_precio = float(precio_promocional)
                p_foto = s.producto_color.producto.foto
                if s.producto_color.producto.categoria:
                    p_cat_nom = s.producto_color.producto.categoria.nombre
                    p_cat_id = s.producto_color.producto.categoria_id

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
            "precio_original": float(precio_original) if p_precio is not None else None,
            "porcentaje_promocion": porcentaje_promocion if p_precio is not None else 0,
            "precio_variante": float(s.precio_variante) if s.precio_variante is not None else None,
            "medidas": s.medidas or {},
            "producto_color_id": s.producto_color_id,
            "color": color_nom,
            "color_nombre": color_nom,
            "talla_id": s.talla_id,
            "talla": talla_nom,
            "talla_nombre": talla_nom,
            "categoria": p_cat_nom,
            "categoria_nombre": p_cat_nom,
            "categoria_id": p_cat_id,
            "sucursal_id": s.sucursal_id,
            "sucursal": suc_nom,
            "cantidad": s.cantidad,
            "cantidad_disponible": s.cantidad,
        })
    return result



@router.post(
    "/ajustar",
    summary="Ajustar o registrar stock de inventario",
    dependencies=[Depends(require_plan_capability("productos"))],
)
async def ajustar_stock(
    payload: StockAdjustRequest,
    current_user: User = Depends(require_permission("inventario.editar")),
    db: Session = Depends(get_db),
):
    """Crea o actualiza la existencia de stock para una combinación producto-color-talla-sucursal."""
    stock = None
    if payload.stock_inventario_id:
        stock_query = db.query(StockInventario).filter(StockInventario.id == payload.stock_inventario_id)
        stock = scope_by_sucursal(
            stock_query, db, current_user, StockInventario.sucursal_id
        ).first()
        if not stock:
            raise NotFoundException("Registro de inventario no encontrado.")
        stock.cantidad = payload.cantidad
        if payload.precio_variante is not None:
            stock.precio_variante = payload.precio_variante
        if payload.medidas is not None:
            stock.medidas = payload.medidas
    elif payload.producto_color_id and payload.talla_id and payload.sucursal_id:
        get_scoped_sucursal(db, current_user, payload.sucursal_id)
        producto_color = (
            db.query(ProductoColor)
            .join(Producto, Producto.codigo == ProductoColor.producto_codigo)
            .filter(
                ProductoColor.id == payload.producto_color_id,
                Producto.empresa_id == current_user.empresa_id,
            )
            .first()
            if not current_user.is_platform_admin
            else db.query(ProductoColor).filter(ProductoColor.id == payload.producto_color_id).first()
        )
        if not producto_color:
            raise NotFoundException("Variante de producto no encontrada.")
        talla = scope_by_empresa(
            db.query(Talla), current_user, Talla.empresa_id
        ).filter(Talla.id == payload.talla_id).first()
        if not talla:
            raise NotFoundException("Talla no encontrada.")
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
            if payload.precio_variante is not None:
                stock.precio_variante = payload.precio_variante
            if payload.medidas is not None:
                stock.medidas = payload.medidas
        else:
            stock = StockInventario(
                producto_color_id=payload.producto_color_id,
                talla_id=payload.talla_id,
                sucursal_id=payload.sucursal_id,
                cantidad=payload.cantidad,
                precio_variante=payload.precio_variante,
                medidas=payload.medidas or {},
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
        "precio_variante": float(stock.precio_variante) if stock.precio_variante is not None else None,
        "medidas": stock.medidas or {},
    }
