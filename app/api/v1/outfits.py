"""
Endpoints de la API para Combinación de Outfits (Punto 9 / v7).
Permite crear, listar, eliminar y comprar combinaciones completas de prendas en un clic.
"""
from datetime import datetime
from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.stock_inventario import StockInventario
from app.models.outfit import Outfit, OutfitItem
from app.models.carrito import Carrito, DetalleCarrito
from app.schemas.outfit import OutfitCreate, OutfitResponse, OutfitItemResponse
from app.api.deps import get_current_user
from app.api.v1.carrito import _get_or_create_cliente
from app.services.bitacora_service import BitacoraService

router = APIRouter(prefix="/outfits", tags=["Outfits y Combinaciones"])


def _serialize_outfit(outfit: Outfit) -> dict:
    items_data = []
    for item in outfit.items:
        prod_nom = item.producto.nombre if item.producto else None
        prod_foto = item.producto.foto if item.producto else None
        prod_precio = item.producto.precio if item.producto else item.precio
        items_data.append({
            "id": item.id,
            "producto_codigo": item.producto_codigo,
            "tipo_prenda": item.tipo_prenda,
            "precio": item.precio,
            "producto_nombre": prod_nom,
            "producto_foto": prod_foto,
            "producto_precio": prod_precio,
        })
    return {
        "id": outfit.id,
        "user_id": outfit.user_id,
        "nombre": outfit.nombre,
        "descripcion": outfit.descripcion,
        "total": outfit.total,
        "created_at": outfit.created_at,
        "items": items_data,
    }


@router.get("", response_model=List[OutfitResponse], summary="Listar outfits del usuario actual")
async def get_my_outfits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna todas las combinaciones de outfits guardadas por el usuario actual."""
    outfits = (
        db.query(Outfit)
        .filter(Outfit.user_id == current_user.id)
        .order_by(Outfit.created_at.desc())
        .all()
    )
    return [_serialize_outfit(o) for o in outfits]


@router.post("", response_model=OutfitResponse, status_code=status.HTTP_201_CREATED, summary="Guardar nuevo outfit")
async def create_outfit(
    payload: OutfitCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea una nueva combinación de prendas personalizada para el usuario actual."""
    total_acumulado = Decimal("0.00")
    items_to_add = []

    for item_in in payload.items:
        producto = db.query(Producto).filter(Producto.codigo == item_in.producto_codigo).first()
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con código '{item_in.producto_codigo}' no encontrado.",
            )
        precio_item = producto.precio
        total_acumulado += precio_item

        outfit_item = OutfitItem(
            producto_codigo=producto.codigo,
            tipo_prenda=item_in.tipo_prenda,
            precio=precio_item,
        )
        items_to_add.append(outfit_item)

    nuevo_outfit = Outfit(
        user_id=current_user.id,
        nombre=payload.nombre.strip(),
        descripcion=payload.descripcion.strip() if payload.descripcion else None,
        total=total_acumulado,
    )
    db.add(nuevo_outfit)
    db.flush()

    for it in items_to_add:
        it.outfit_id = nuevo_outfit.id
        db.add(it)

    db.commit()
    db.refresh(nuevo_outfit)

    try:
        BitacoraService.registrar(
            db=db,
            user=current_user,
            action=f"Guardó outfit '{nuevo_outfit.nombre}' con {len(items_to_add)} prendas (Total: Bs {nuevo_outfit.total})",
            module="outfits",
        )
    except Exception as e:
        print(f"Warning bitácora outfit: {e}")

    return _serialize_outfit(nuevo_outfit)


@router.delete("/{outfit_id}", status_code=status.HTTP_200_OK, summary="Eliminar outfit guardado")
async def delete_outfit(
    outfit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Elimina un outfit guardado por el usuario."""
    outfit = db.query(Outfit).filter(Outfit.id == outfit_id).first()
    if not outfit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outfit no encontrado.")

    if outfit.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar este outfit.",
        )

    nombre_eliminado = outfit.nombre
    db.delete(outfit)
    db.commit()

    try:
        BitacoraService.registrar(
            db=db,
            user=current_user,
            action=f"Eliminó outfit #{outfit_id} ('{nombre_eliminado}')",
            module="outfits",
        )
    except Exception as e:
        print(f"Warning bitácora outfit delete: {e}")

    return {"message": f"Outfit '{nombre_eliminado}' eliminado correctamente."}


@router.post("/{outfit_id}/comprar", summary="Comprar todo el outfit (agrega al carrito activo)")
async def buy_outfit(
    outfit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Agrega todas las prendas del outfit al carrito activo del cliente en un solo clic.
    Selecciona automáticamente inventario disponible con stock para cada prenda.
    """
    outfit = db.query(Outfit).filter(Outfit.id == outfit_id).first()
    if not outfit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outfit no encontrado.")

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

    agregados = []
    sin_stock = []

    for item in outfit.items:
        # Buscar stock disponible para el producto
        stock = (
            db.query(StockInventario)
            .join(ProductoColor, StockInventario.producto_color_id == ProductoColor.id)
            .filter(
                ProductoColor.producto_codigo == item.producto_codigo,
                StockInventario.cantidad > 0,
            )
            .first()
        )

        if not stock:
            # Buscar sin filtro de cantidad para verificar si al menos existe
            sin_stock.append(item.producto.nombre if item.producto else item.producto_codigo)
            continue

        # Verificar si ya existe en carrito
        existing = (
            db.query(DetalleCarrito)
            .filter(
                DetalleCarrito.carrito_id == carrito.id,
                DetalleCarrito.stock_inventario_id == stock.id,
            )
            .first()
        )

        if existing:
            if stock.cantidad >= existing.cantidad + 1:
                existing.cantidad += 1
                agregados.append(item.producto.nombre if item.producto else item.producto_codigo)
            else:
                sin_stock.append(f"{item.producto.nombre} (Stock al límite)")
        else:
            detalle = DetalleCarrito(
                carrito_id=carrito.id,
                stock_inventario_id=stock.id,
                cantidad=1,
                precio_unitario=item.precio,
            )
            db.add(detalle)
            agregados.append(item.producto.nombre if item.producto else item.producto_codigo)

    db.commit()
    db.refresh(carrito)

    try:
        BitacoraService.registrar(
            db=db,
            user=current_user,
            action=f"Agregó al carrito el outfit '{outfit.nombre}' ({len(agregados)} prendas agregadas)",
            module="outfits",
        )
    except Exception as e:
        print(f"Warning bitácora outfit comprar: {e}")

    return {
        "message": f"Se procesó el outfit '{outfit.nombre}'.",
        "outfit_id": outfit.id,
        "items_agregados": agregados,
        "items_sin_stock": sin_stock,
        "total_carrito_items": len(carrito.items),
    }
