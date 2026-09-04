"""
Pydantic schemas for Sucursales (Store Branches).
"""
from datetime import datetime
import re
from pydantic import BaseModel, Field, field_validator


class SucursalBase(BaseModel):
    """Base schema for Sucursal."""

    name: str = Field(..., min_length=2, max_length=150, description="Branch name")
    city: str = Field(..., min_length=2, max_length=100, description="City where branch is located")
    address: str = Field(..., min_length=5, max_length=255, description="Street address")
    phone: str = Field(..., min_length=7, max_length=20, description="Contact phone number")
    active: bool = Field(default=True, description="Whether branch is operational")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^[0-9+\-\s]{7,20}$", v):
            raise ValueError("El teléfono solo debe contener dígitos, espacios, o símbolos '+' y '-' (entre 7 y 20 caracteres).")
        return v.strip()


class SucursalCreate(SucursalBase):
    """Schema for creating a branch."""
    pass


class SucursalUpdate(BaseModel):
    """Schema for updating a branch."""

    name: str | None = Field(None, min_length=2, max_length=150)
    city: str | None = Field(None, min_length=2, max_length=100)
    address: str | None = Field(None, min_length=5, max_length=255)
    phone: str | None = Field(None, min_length=7, max_length=20)
    active: bool | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^[0-9+\-\s]{7,20}$", v):
            raise ValueError("El teléfono solo debe contener dígitos, espacios, o símbolos '+' y '-' (entre 7 y 20 caracteres).")
        return v.strip() if v is not None else None


class SucursalResponse(SucursalBase):
    """Schema for returning branch details."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
