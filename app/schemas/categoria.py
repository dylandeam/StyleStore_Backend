"""
Pydantic schemas para Categorias (CU11).
"""
from datetime import datetime
from pydantic import BaseModel, Field


class CategoriaCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)


class CategoriaUpdate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)


class CategoriaResponse(BaseModel):
    id: int
    nombre: str
    created_at: datetime

    model_config = {"from_attributes": True}
