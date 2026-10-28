"""
Pydantic schemas para Stock_Inventario.
Conforme a Especificación StyleStore v4.
"""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class StockItemUpdate(BaseModel):
    """Línea para actualizar stock de una combinación específica."""

    color_id: int | None = None
    producto_color_id: int | None = None
    talla_id: int
    sucursal_id: int
    cantidad: int = Field(..., ge=0)
    precio_variante: Decimal | None = Field(None, gt=Decimal("0"), max_digits=12, decimal_places=2)


class StockBulkUpdateRequest(BaseModel):
    """Lote de actualización de stock para un producto."""

    items: list[StockItemUpdate]


class StockInventarioResponse(BaseModel):
    id: int
    producto_codigo: str
    color_id: int
    producto_color_id: int | None = None
    color_nombre: str
    talla_id: int
    talla_nombre: str
    sucursal_id: int
    sucursal_nombre: str
    cantidad: int
    precio_variante: Decimal | None = None
    precio_efectivo: Decimal
    updated_at: datetime

    model_config = {"from_attributes": True}
