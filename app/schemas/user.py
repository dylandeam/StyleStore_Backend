"""
Pydantic schemas for user data.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for creating a user (internal use)."""

    email: EmailStr
    name: str
    hashed_password: str


class UserResponse(BaseModel):
    """Schema for returning user data in API responses."""

    id: int = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., description="User full name")
    is_active: bool = Field(..., description="Whether the user is active")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = {"from_attributes": True}
