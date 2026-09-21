"""
Pydantic schemas para Productos (CU10 / v5).
Conforme a Especificación StyleStore v5 (Sección 13 y 14).
PK: codigo.
FK: categoria_id, temporada_id, coleccion_id.
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
    foto_trasera: str | None = None
    foto_vestidor_frontal: str | None = None
    foto_vestidor_trasera: str | None = None
    tipo_prenda: str = Field("superior", description="superior, inferior, cuerpo_entero, accesorio")
    puntos_clave_ia: str | None = Field(None, description="JSON con puntos clave y configuración de manga/entalle IA")
    precio: Decimal = Field(..., gt=Decimal("0"))
    categoria_id: int
    temporada_id: int
    coleccion_id: int | None = Field(None, description="ID de colección de prendas")
    color_ids: list[int] = Field(default_factory=list, description="IDs de colores habilitados")
    active: bool = True
    visible_en_catalogo: bool = True


class ProductoUpdate(BaseModel):
    """Schema para actualizar producto existente."""

    nombre: str | None = None
    descripcion: str | None = None
    foto: str | None = None
    foto_trasera: str | None = None
    foto_vestidor_frontal: str | None = None
    foto_vestidor_trasera: str | None = None
    tipo_prenda: str | None = None
    puntos_clave_ia: str | None = None
    precio: Decimal | None = Field(None, gt=Decimal("0"))
    categoria_id: int | None = None
    temporada_id: int | None = None
    coleccion_id: int | None = None
    color_ids: list[int] | None = None
    active: bool | None = None
    visible_en_catalogo: bool | None = None


class ProductoResponse(BaseModel):
    """Schema para exponer producto en la API con detalles de catálogo e inventario."""

    codigo: str
    nombre: str
    descripcion: str | None = None
    foto: str | None = None
    foto_trasera: str | None = None
    foto_vestidor_frontal: str | None = None
    foto_vestidor_trasera: str | None = None
    tipo_prenda: str = "superior"
    puntos_clave_ia: str | None = None
    precio: Decimal
    categoria_id: int
    categoria_nombre: str | None = None
    temporada_id: int
    temporada_nombre: str | None = None
    coleccion_id: int | None = None
    coleccion_nombre: str | None = None
    active: bool
    visible_en_catalogo: bool = True

    colores: list[ColorResponse] = Field(default_factory=list)
    stock_total: int = 0

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
