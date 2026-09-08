"""
Pydantic schemas para Proveedores (CU16).
Conforme a Especificación StyleStore v4 (Diagrama DB Oficial).
Sin CI según diagrama oficial v4.
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class ProveedorCreate(BaseModel):
    codigo: str | None = Field(None, description="Código de negocio (se autogenera PROV-XXXX si se omite)")
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    telefono: str = Field(..., min_length=5, max_length=20)


class ProveedorUpdate(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    email: EmailStr | None = None
    telefono: str | None = None


class ProveedorResponse(BaseModel):
    codigo: str
    nombre: str
    apellido: str
    email: str
    telefono: str

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
