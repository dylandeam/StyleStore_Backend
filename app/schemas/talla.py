"""
Pydantic schemas para Tallas (CU13).
"""
from datetime import datetime
from pydantic import BaseModel, Field


class TallaCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=20)


class TallaUpdate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=20)


class TallaResponse(BaseModel):
    id: int
    nombre: str
    created_at: datetime

    model_config = {"from_attributes": True}
