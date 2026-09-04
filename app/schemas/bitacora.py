"""
Pydantic schemas for Bitacora (Audit Log) (CU6).
"""
from datetime import datetime
from pydantic import BaseModel, Field


class BitacoraResponse(BaseModel):
    """Schema for returning bitacora log entry."""

    id: int
    user_id: int | None = None
    user_snapshot: str = Field(..., description="User email or name at time of event")
    action: str = Field(..., description="Description of the action performed")
    module: str | None = Field(None, description="Module where action occurred")
    created_at: datetime = Field(..., description="Timestamp of the event")

    model_config = {"from_attributes": True}


class BitacoraPageResponse(BaseModel):
    """Paginated bitacora response."""

    items: list[BitacoraResponse]
    total: int
    page: int
    size: int
    pages: int
