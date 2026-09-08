"""
Pydantic schemas para Stock_Inventario.
Conforme a Especificación StyleStore v4.
"""
from datetime import datetime
from pydantic import BaseModel, Field


class StockItemUpdate(BaseModel):
    """Línea para actualizar stock de una combinación específica."""

    color_id: int
    talla_id: int
    sucursal_id: int
    cantidad: int = Field(..., ge=0)


class StockBulkUpdateRequest(BaseModel):
    """Lote de actualización de stock para un producto."""

    items: list[StockItemUpdate]


class StockInventarioResponse(BaseModel):
    id: int
    producto_codigo: str
    color_id: int
    color_nombre: str
    talla_id: int
    talla_nombre: str
    sucursal_id: int
    sucursal_nombre: str
    cantidad: int
    updated_at: datetime

    model_config = {"from_attributes": True}
