"""Pydantic schemas for SaaS companies (tenants)."""
from datetime import datetime
import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class EmpresaCreate(BaseModel):
    codigo: str = Field(..., min_length=2, max_length=50)
    nombre: str = Field(..., min_length=2, max_length=150)
    admin_email: EmailStr
    admin_name: str = Field(..., min_length=2, max_length=100)
    admin_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("codigo")
    @classmethod
    def validate_codigo(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", normalized):
            raise ValueError("El código solo admite letras minúsculas, números, guion y guion bajo.")
        return normalized

    @field_validator("admin_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[a-z]", value) or not re.search(r"[A-Z]", value) or not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("La contraseña debe incluir mayúscula, minúscula y carácter especial.")
        return value


class EmpresaResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmpresaConAdminResponse(EmpresaResponse):
    admin_user_id: int
