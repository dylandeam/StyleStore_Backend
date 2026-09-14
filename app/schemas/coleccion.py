"""
Pydantic schemas for Colecciones (CU15 / v5).
"""
from datetime import datetime
from pydantic import BaseModel, Field


class ColeccionBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100, description="Nombre único de la colección")
    descripcion: str | None = Field(None, description="Descripción opcional de la colección")


class ColeccionCreate(ColeccionBase):
    pass


class ColeccionUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=100)
    descripcion: str | None = None
    active: bool | None = None


class ColeccionResponse(ColeccionBase):
    id: int
    active: bool
    productos_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
