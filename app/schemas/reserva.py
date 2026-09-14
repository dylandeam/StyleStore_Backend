"""
Pydantic schemas para Reservas (v5 sección 16).
"""
from datetime import date, time, datetime
from pydantic import BaseModel, Field


class DetalleReservaCreate(BaseModel):
    stock_inventario_id: int
    cantidad: int = Field(1, ge=1)


class DetalleReservaResponse(BaseModel):
    id: int
    stock_inventario_id: int
    cantidad: int
    producto_codigo: str | None = None
    producto_nombre: str | None = None
    color_nombre: str | None = None
    talla_nombre: str | None = None
    foto: str | None = None

    model_config = {"from_attributes": True}


class ReservaCreate(BaseModel):
    sucursal_id: int
    items: list[DetalleReservaCreate] = Field(..., min_length=1)


class ReservaEstadoUpdate(BaseModel):
    estado: str = Field(..., description="Nuevo estado: 'pendiente', 'completada', 'cancelada'")


class ReservaResponse(BaseModel):
    id: int
    fecha: date
    hora: time
    estado: str
    codigo_cliente: str
    cliente_nombre: str | None = None
    sucursal_id: int
    sucursal_ciudad: str | None = None
    sucursal_direccion: str | None = None
    detalles: list[DetalleReservaResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
