"""
Pydantic schemas para Proveedores (CU16).
Conforme a Especificación StyleStore v5 (Sección 10).
Con CI obligatorio y multiasociaciones independientes (Categorias, Temporadas, Colecciones).
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class SimpleItem(BaseModel):
    id: int
    nombre: str

    model_config = {"from_attributes": True}


class ProveedorCreate(BaseModel):
    ci: str | None = Field(None, max_length=20, description="Cédula de identidad única")
    codigo: str | None = Field(None, description="Código de negocio opcional")
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    telefono: str = Field(..., min_length=5, max_length=20)
    categoria_ids: list[int] = Field(default_factory=list, description="IDs de categorías suministradas")
    temporada_ids: list[int] = Field(default_factory=list, description="IDs de temporadas suministradas")
    coleccion_ids: list[int] = Field(default_factory=list, description="IDs de colecciones suministradas")


class ProveedorUpdate(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    email: EmailStr | None = None
    telefono: str | None = None
    ci: str | None = None
    categoria_ids: list[int] | None = None
    temporada_ids: list[int] | None = None
    coleccion_ids: list[int] | None = None


class ProveedorResponse(BaseModel):
    codigo: str
    ci: str | None = None
    nombre: str
    apellido: str
    email: str
    telefono: str
    categorias: list[SimpleItem] = []
    temporadas: list[SimpleItem] = []
    colecciones: list[SimpleItem] = []

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
