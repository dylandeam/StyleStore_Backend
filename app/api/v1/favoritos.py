"""Lista de deseos aislada por usuario y tenant activo."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.favorito import Favorito
from app.models.producto import Producto
from app.models.user import User
from app.schemas.favorito import FavoritoEstadoResponse, FavoritoResponse

router = APIRouter(prefix="/favoritos", tags=["Favoritos"])


def _tenant_id(user: User) -> int:
    if user.empresa_id is None or user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Selecciona un tenant de cliente para gestionar favoritos.",
        )
    return user.empresa_id


def _serialize(item: Favorito) -> dict:
    product = item.producto
    return {
        "id": item.id,
        "empresa_id": item.empresa_id,
        "producto_codigo": item.producto_codigo,
        "created_at": item.created_at,
        "producto_nombre": product.nombre,
        "producto_foto": product.foto,
        "precio": float(product.precio),
        "precio_descuento": float(product.precio_descuento) if product.precio_descuento is not None else None,
        "en_promocion": bool(product.en_promocion),
    }


@router.get("", response_model=list[FavoritoResponse], summary="Listar mis productos favoritos")
async def list_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    empresa_id = _tenant_id(current_user)
    items = (
        db.query(Favorito)
        .join(Producto, Favorito.producto_codigo == Producto.codigo)
        .filter(
            Favorito.user_id == current_user.id,
            Favorito.empresa_id == empresa_id,
            Producto.empresa_id == empresa_id,
            Producto.active.is_(True),
            Producto.visible_en_catalogo.is_(True),
        )
        .order_by(Favorito.created_at.desc())
        .all()
    )
    return [_serialize(item) for item in items]


@router.post(
    "/{producto_codigo}",
    response_model=FavoritoEstadoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Guardar producto en favoritos",
)
async def add_favorite(
    producto_codigo: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    empresa_id = _tenant_id(current_user)
    product = db.query(Producto).filter(
        Producto.codigo == producto_codigo,
        Producto.empresa_id == empresa_id,
        Producto.active.is_(True),
        Producto.visible_en_catalogo.is_(True),
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado en el tenant activo.")

    existing = db.query(Favorito).filter(
        Favorito.user_id == current_user.id,
        Favorito.empresa_id == empresa_id,
        Favorito.producto_codigo == product.codigo,
    ).first()
    if not existing:
        db.add(Favorito(
            user_id=current_user.id,
            empresa_id=empresa_id,
            producto_codigo=product.codigo,
        ))
        db.commit()
    return {"producto_codigo": product.codigo, "es_favorito": True}


@router.delete(
    "/{producto_codigo}",
    response_model=FavoritoEstadoResponse,
    summary="Quitar producto de favoritos",
)
async def remove_favorite(
    producto_codigo: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    empresa_id = _tenant_id(current_user)
    item = db.query(Favorito).filter(
        Favorito.user_id == current_user.id,
        Favorito.empresa_id == empresa_id,
        Favorito.producto_codigo == producto_codigo,
    ).first()
    if item:
        db.delete(item)
        db.commit()
    return {"producto_codigo": producto_codigo, "es_favorito": False}

