"""
Pydantic schemas for user data and employee management.
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


class UserCreateByAdmin(BaseModel):
    """Schema for administrator creating employee accounts (CU1)."""

    email: EmailStr = Field(..., description="Employee email address")
    name: str = Field(..., min_length=2, max_length=100, description="Employee first name")
    apellido: str | None = Field(None, min_length=2, max_length=100, description="Employee last name")
    ci: str | None = Field(None, max_length=20, description="Employee CI")
    password: str = Field(..., min_length=8, max_length=100, description="Temporary or initial password")
    role: Literal["cajero", "encargado_sucursal", "administrador"] = Field(
        ..., description="Assigned role for employee"
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[a-z]", v) or not re.search(r"[A-Z]", v) or not re.search(r"[!@#$%^&*()_+\-=\[\]{};:\'\",.<>/?\\|`~]", v):
            raise ValueError("La contraseña debe contener al menos una mayúscula, una minúscula y un carácter especial.")
        return v


class UserUpdateByAdmin(BaseModel):
    """Schema for administrator updating employee info or status."""

    name: str | None = Field(None, min_length=2, max_length=100)
    apellido: str | None = Field(None, min_length=2, max_length=100)
    ci: str | None = Field(None, max_length=20)
    role: Literal["cajero", "encargado_sucursal", "administrador", "cliente"] | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """Schema for returning user data in API responses."""

    id: int = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., description="User full name")
    apellido: str | None = Field(None, description="User last name")
    ci: str | None = Field(None, description="User CI")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether the user is active")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = {"from_attributes": True}

