"""
Pydantic schemas for Password Change request and confirmation (CU4).
"""
import re
from pydantic import BaseModel, Field, field_validator, model_validator


class RequestPasswordChangeRequest(BaseModel):
    """Schema for requesting a password change with email confirmation."""

    current_password: str = Field(..., description="Current user password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")
    new_password_confirmation: str = Field(..., min_length=8, max_length=100, description="New password confirmation")

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v: str) -> str:
        if not re.search(r"[a-z]", v) or not re.search(r"[A-Z]", v) or not re.search(r"[!@#$%^&*()_+\-=\[\]{};:\'\",.<>/?\\|`~]", v):
            raise ValueError("La contraseña debe contener al menos una mayúscula, una minúscula y un carácter especial.")
        return v

    @model_validator(mode="after")
    def validate_password_confirmation_match(self) -> "RequestPasswordChangeRequest":
        if self.new_password != self.new_password_confirmation:
            raise ValueError("La confirmación de la contraseña no coincide con la nueva contraseña.")
        if self.current_password == self.new_password:
            raise ValueError("La nueva contraseña no puede ser igual a la contraseña actual.")
        return self


class ConfirmPasswordChangeRequest(BaseModel):
    """Schema for confirming password change with received token."""

    token: str = Field(..., min_length=10, description="One-time confirmation token from email")
