"""
Pydantic schemas for user data and employee management.
Conforme a Especificación StyleStore v5.
"""
from datetime import datetime
import re
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Schema for creating a user (internal use)."""

    email: EmailStr
    name: str
    hashed_password: str
    role: str = "cliente"
    role_id: int | None = None


class UserProfileUpdateRequest(BaseModel):
    """Schema for user updating their own profile information (CU2 / v5 Sección 2).
    CI is deliberately omitted to prevent changing historical identifier.
    """

    name: str | None = Field(None, min_length=2, max_length=100)
    apellido: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None
    telefono: str | None = Field(None, max_length=20)
    direccion: str | None = Field(None, max_length=255)
    foto: str | None = Field(None, max_length=255)


class UserCreateByAdmin(BaseModel):
    """Schema for administrator creating user or employee accounts (CU1 / v5 Sección 4)."""

    email: EmailStr = Field(..., description="Correo electrónico")
    name: str = Field(..., min_length=2, max_length=100, description="Nombres")
    apellido: str | None = Field(None, min_length=2, max_length=100, description="Apellidos")
    ci: str | None = Field(None, max_length=20, description="Cédula de Identidad")
    password: str | None = Field(None, description="Contraseña opcional (por defecto igual al CI)")
    role: str = Field(..., description="Nombre o código del rol asignado")
    role_id: int | None = Field(None, description="ID opcional del rol asignado")


class UserUpdateByAdmin(BaseModel):
    """Schema for administrator updating employee info or status."""

    name: str | None = Field(None, min_length=2, max_length=100)
    apellido: str | None = Field(None, min_length=2, max_length=100)
    ci: str | None = Field(None, max_length=20)
    telefono: str | None = Field(None, max_length=20)
    direccion: str | None = Field(None, max_length=255)
    role: str | None = None
    role_id: int | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """Schema for returning user data in API responses."""

    id: int = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., description="User full name")
    apellido: str | None = Field(None, description="User last name")
    ci: str | None = Field(None, description="User CI")
    telefono: str | None = Field(None, description="User phone")
    direccion: str | None = Field(None, description="User address")
    foto: str | None = Field(None, description="Profile photo URL")
    role_id: int | None = Field(None, description="Role ID")
    role: str = Field(..., description="User role")
    sucursal_id: int | None = Field(None, description="ID de sucursal si es empleado")
    is_active: bool = Field(..., description="Whether the user is active")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = {"from_attributes": True}
