"""
Schemas Pydantic para el módulo de Compras a Proveedores (Punto 2 / v7).
"""
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field


class DetalleCompraCreate(BaseModel):
    producto_codigo: str = Field(..., description="Código de la prenda")
    color_id: int = Field(..., description="ID del color")
    talla_id: int = Field(..., description="ID de la talla")
    cantidad: int = Field(..., gt=0, description="Cantidad adquirida")
    costo_unitario: Decimal = Field(..., gt=0, description="Precio unitario de costo")


class DetalleCompraResponse(BaseModel):
    id: int
    producto_codigo: str
    producto_nombre: str | None = None
    color_id: int
    color_nombre: str | None = None
    talla_id: int
    talla_nombre: str | None = None
    cantidad: int
    costo_unitario: Decimal
    subtotal: Decimal

    model_config = {"from_attributes": True}


class CompraCreate(BaseModel):
    proveedor_codigo: str = Field(..., description="Código del proveedor")
    sucursal_id: int = Field(..., description="ID de la sucursal de destino del stock")
    nro_factura: str | None = Field(None, description="Número de factura o comprobante del proveedor")
    observaciones: str | None = Field(None, description="Notas u observaciones de la compra")
    items: list[DetalleCompraCreate] = Field(..., min_length=1, description="Lista de prendas a ingresar")


class CompraResponse(BaseModel):
    id: int
    fecha: date
    proveedor_codigo: str
    proveedor_nombre: str | None = None
    sucursal_id: int
    sucursal_nombre: str | None = None
    nro_factura: str | None = None
    total: Decimal
    estado: str
    observaciones: str | None = None
    created_at: datetime
    detalles: list[DetalleCompraResponse] = []

    model_config = {"from_attributes": True}
