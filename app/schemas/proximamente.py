"""
Pydantic schemas for Próximamente (v5 sección 11).
"""
from datetime import datetime, date
from pydantic import BaseModel, Field


class ProximamenteBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150)
    descripcion: str | None = None
    foto: str | None = None
    fecha_estimada_llegada: date | None = None
    proveedor_codigo: str | None = None
    categoria_id: int | None = None
    temporada_id: int | None = None
    coleccion_id: int | None = None


class ProximamenteCreate(ProximamenteBase):
    pass


class ProximamenteUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=150)
    descripcion: str | None = None
    foto: str | None = None
    fecha_estimada_llegada: date | None = None
    proveedor_codigo: str | None = None
    categoria_id: int | None = None
    temporada_id: int | None = None
    coleccion_id: int | None = None
    active: bool | None = None


class ProximamenteResponse(ProximamenteBase):
    id: int
    active: bool
    created_at: datetime
    updated_at: datetime
    categoria_nombre: str | None = None
    temporada_nombre: str | None = None
    coleccion_nombre: str | None = None
    proveedor_nombre: str | None = None

    model_config = {"from_attributes": True}
