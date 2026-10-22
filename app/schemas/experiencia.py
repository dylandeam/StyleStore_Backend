"""Contratos para calificaciones y reclamos poscompra."""
from datetime import date, datetime

from pydantic import BaseModel, Field


class CalificacionCreate(BaseModel):
    orden_venta_id: int
    puntuacion: int = Field(..., ge=1, le=5)
    comentario: str | None = Field(None, max_length=1500)


class CalificacionResponse(BaseModel):
    id: int
    empresa_id: int
    empresa_nombre: str | None = None
    user_id: int
    cliente_nombre: str | None = None
    orden_venta_id: int
    sucursal_id: int | None = None
    sucursal_nombre: str | None = None
    puntuacion: int
    comentario: str | None = None
    created_at: datetime
    sugerir_reclamo: bool = False
    mensaje: str | None = None


class ReclamoCreate(BaseModel):
    sucursal_id: int
    fecha_incidente: date
    motivo: str = Field(..., min_length=2, max_length=40)
    descripcion: str = Field(..., min_length=10, max_length=3000)
    orden_venta_id: int | None = None
    calificacion_id: int | None = None


class ReclamoUpdate(BaseModel):
    estado: str = Field(..., pattern="^(recibido|en_revision|resuelto|rechazado)$")
    respuesta: str | None = Field(None, max_length=3000)


class ReclamoResponse(BaseModel):
    id: int
    empresa_id: int
    empresa_nombre: str | None = None
    user_id: int
    cliente_nombre: str | None = None
    orden_venta_id: int | None = None
    calificacion_id: int | None = None
    sucursal_id: int
    sucursal_nombre: str | None = None
    fecha_incidente: date
    motivo: str
    descripcion: str
    estado: str
    respuesta: str | None = None
    created_at: datetime
    updated_at: datetime

