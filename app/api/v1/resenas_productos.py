"""Endpoints de reseñas públicas por prenda."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.resena_producto import ResenaProductoUpsert, ResenasProductoResponse
from app.services.resena_producto_service import ResenaProductoService


router = APIRouter(prefix="/productos/{codigo}/resenas", tags=["Reseñas de productos"])


@router.get("", response_model=ResenasProductoResponse)
async def list_product_reviews(
    codigo: str,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    return ResenaProductoService(db).list_for_product(codigo, current_user)


@router.put("/mia", response_model=ResenasProductoResponse)
async def save_my_product_review(
    codigo: str,
    payload: ResenaProductoUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ResenaProductoService(db).upsert(codigo, payload, current_user)


@router.delete("/mia", response_model=ResenasProductoResponse)
async def delete_my_product_review(
    codigo: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ResenaProductoService(db).delete_own(codigo, current_user)

