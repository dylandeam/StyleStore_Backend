"""
Pydantic schemas para Clientes (CU9).
Sin foto según diagrama oficial v4.
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class ClienteCreate(BaseModel):
    """Schema para registrar cliente."""

    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    ci: str = Field(..., min_length=4, max_length=20)
    email: EmailStr
    password: str = Field(..., min_length=8)

    telefono: str = Field(..., min_length=5, max_length=20)
    direccion: str = Field(..., min_length=3, max_length=255)


class ClienteUpdate(BaseModel):
    """Schema para actualizar cliente."""

    nombre: str | None = None
    apellido: str | None = None
    ci: str | None = None
    telefono: str | None = None
    direccion: str | None = None


class ClienteResponse(BaseModel):
    """Schema de respuesta para cliente."""

    codigo: str
    user_id: int
    telefono: str
    direccion: str

    nombre: str | None = None
    apellido: str | None = None
    ci: str | None = None
    email: str | None = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
