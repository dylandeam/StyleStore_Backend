"""
Schemas Pydantic para Combinación de Outfits (Punto 9 / v7).
"""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class OutfitItemCreate(BaseModel):
    producto_codigo: str = Field(..., description="Código del producto")
    tipo_prenda: str = Field(
        ...,
        description="Categoría en el outfit: superior, inferior, calzado, accesorio",
    )
    precio: Decimal | None = Field(None, description="Precio unitario referencial")
    stock_inventario_id: int | None = Field(None, description="ID de inventario opcional")


class OutfitItemResponse(BaseModel):
    id: int
    producto_codigo: str
    tipo_prenda: str
    precio: Decimal
    producto_nombre: str | None = None
    producto_foto: str | None = None
    producto_precio: Decimal | None = None

    model_config = {"from_attributes": True}


class OutfitCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150, description="Nombre del look/outfit")
    descripcion: str | None = Field(None, description="Detalles u ocasión del outfit")
    items: list[OutfitItemCreate] = Field(..., min_length=1, description="Lista de prendas del outfit")


class OutfitResponse(BaseModel):
    id: int
    user_id: int
    nombre: str
    descripcion: str | None = None
    total: Decimal
    created_at: datetime
    items: list[OutfitItemResponse] = []

    model_config = {"from_attributes": True}
