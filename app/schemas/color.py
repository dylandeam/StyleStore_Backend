"""
Pydantic schemas para Colores (CU12).
"""
from datetime import datetime
from pydantic import BaseModel, Field


class ColorCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=50)


class ColorUpdate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=50)


class ColorResponse(BaseModel):
    id: int
    nombre: str
    created_at: datetime

    model_config = {"from_attributes": True}
