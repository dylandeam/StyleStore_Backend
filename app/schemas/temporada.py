"""
Pydantic schemas para Temporadas (CU14).
"""
from datetime import datetime
from pydantic import BaseModel, Field


class TemporadaCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)


class TemporadaUpdate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)


class TemporadaResponse(BaseModel):
    id: int
    nombre: str
    created_at: datetime

    model_config = {"from_attributes": True}
