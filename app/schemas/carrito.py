"""
Pydantic schemas para Carrito de Compras (v5 sección 17 y 18).
"""
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class DetalleCarritoCreate(BaseModel):
    stock_inventario_id: int
    cantidad: int = Field(1, ge=1)


class DetalleCarritoUpdate(BaseModel):
    cantidad: int = Field(..., ge=0)


class DetalleCarritoResponse(BaseModel):
    id: int
    stock_inventario_id: int
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal = Decimal("0.00")
    producto_codigo: str | None = None
    producto_nombre: str | None = None
    color_nombre: str | None = None
    talla_nombre: str | None = None
    sucursal_nombre: str | None = None
    foto: str | None = None

    model_config = {"from_attributes": True}


class CarritoResponse(BaseModel):
    id: int
    fecha: date
    estado: str
    codigo_cliente: str
    items: list[DetalleCarritoResponse] = []
    total: Decimal = Decimal("0.00")
    created_at: datetime

    model_config = {"from_attributes": True}


class ConfirmarCarritoRequest(BaseModel):
    sucursal_id: int | None = None
