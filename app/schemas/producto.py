"""
Pydantic schemas para Productos (CU10).
Conforme a Especificación StyleStore v4 (Diagrama DB Oficial).
PK: codigo.
"""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from app.schemas.color import ColorResponse


class ProductoCreate(BaseModel):
    """Schema para crear un nuevo producto."""

    codigo: str | None = Field(None, description="Código de negocio (se autogenera PROD-XXXX si se omite)")
    nombre: str = Field(..., min_length=2, max_length=150)
    descripcion: str | None = None
    foto: str | None = None
    precio: Decimal = Field(..., gt=0)
    categoria_id: int
    temporada_id: int
    color_ids: list[int] = Field(default_factory=list, description="IDs de colores habilitados")
    active: bool = True


class ProductoUpdate(BaseModel):
    """Schema para actualizar producto existente."""

    nombre: str | None = None
    descripcion: str | None = None
    foto: str | None = None
    precio: Decimal | None = Field(None, gt=0)
    categoria_id: int | None = None
    temporada_id: int | None = None
    color_ids: list[int] | None = None
    active: bool | None = None


class ProductoResponse(BaseModel):
    """Schema para exponer producto en la API con detalles de catálogo e inventario."""

    codigo: str
    nombre: str
    descripcion: str | None = None
    foto: str | None = None
    precio: Decimal
    categoria_id: int
    categoria_nombre: str | None = None
    temporada_id: int
    temporada_nombre: str | None = None
    active: bool

    colores: list[ColorResponse] = Field(default_factory=list)
    stock_total: int = 0

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
