"""
Pydantic schemas for authentication requests and responses.
"""
import re
from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Schema for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., min_length=8, max_length=100,
        description="Password (min 8 characters)"
    )
    name: str = Field(
        ..., min_length=2, max_length=100,
        description="User full name or first name"
    )
    apellido: str | None = Field(None, max_length=100, description="User last name")
    ci: str | None = Field(None, max_length=20, description="Carnet de Identidad")
    telefono: str | None = Field(None, max_length=20, description="Número de teléfono o celular")
    direccion: str | None = Field(None, max_length=255, description="Dirección de domicilio")
    foto: str | None = Field(None, max_length=255, description="URL o path de la foto de perfil")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[a-z]", v) or not re.search(r"[A-Z]", v) or not re.search(r"[!@#$%^&*()_+\-=\[\]{};:\'\",.<>/?\\|`~]", v):
            raise ValueError("La contraseña debe contener al menos una mayúscula, una minúscula y un carácter especial.")
        return v


class LoginRequest(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Schema for token response after login."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh."""

    refresh_token: str = Field(..., description="JWT refresh token")
