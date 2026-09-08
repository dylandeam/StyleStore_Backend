"""
Pydantic schemas para Empleados (CU8).
"""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field


class EmpleadoCreate(BaseModel):
    """Schema para registrar empleado junto con su cuenta de usuario."""

    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    ci: str = Field(..., min_length=4, max_length=20)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field(default="encargado_sucursal")

    sucursal_id: int
    edad: int = Field(..., ge=18, le=100)
    sueldo: Decimal = Field(..., ge=0)
    telefono: str = Field(..., min_length=5, max_length=20)
    direccion: str = Field(..., min_length=3, max_length=255)
    foto: str | None = None


class EmpleadoUpdate(BaseModel):
    """Schema para actualizar datos de empleado."""

    nombre: str | None = None
    apellido: str | None = None
    ci: str | None = None
    role: str | None = None
    sucursal_id: int | None = None
    edad: int | None = Field(None, ge=18, le=100)
    sueldo: Decimal | None = Field(None, ge=0)
    telefono: str | None = None
    direccion: str | None = None
    foto: str | None = None


class EmpleadoResponse(BaseModel):
    """Schema para exponer empleado en la API."""

    codigo: str
    user_id: int
    sucursal_id: int
    edad: int
    sueldo: Decimal
    telefono: str
    direccion: str
    foto: str | None = None

    # Datos del usuario asociado
    nombre: str | None = None
    apellido: str | None = None
    ci: str | None = None
    email: str | None = None
    role: str | None = None
    sucursal_nombre: str | None = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
