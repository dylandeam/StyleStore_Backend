"""Versioned contract for idempotent offline operations."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SyncOperationRequest(BaseModel):
    operation_uuid: UUID
    operation_type: Literal["reserva", "venta_efectivo"]
    payload_version: Literal[1] = 1
    client_created_at: datetime
    payload: dict


class SyncOperationResponse(BaseModel):
    operation_uuid: UUID
    operation_type: str
    status: Literal["procesando", "confirmada", "rechazada", "conflicto"]
    reason: str | None = None
    result_type: str | None = None
    result_id: int | None = None
    refund_id: int | None = None
    refund_status: str | None = None
    refund_amount: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SyncBatchRequest(BaseModel):
    operations: list[SyncOperationRequest] = Field(..., min_length=1, max_length=50)
