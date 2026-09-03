"""
Common Pydantic schemas used across the application.
"""
from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str = Field(..., description="Response message")


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str = Field(..., description="Error description")
