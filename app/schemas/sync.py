"""Versioned contract for idempotent offline operations."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SyncOperationRequest(BaseModel):
    operation_uuid: UUID
    operation_type: Literal["reserva", "venta_efectivo", "resena_producto"]
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


class SyncDiagnosticoItem(BaseModel):
    operation_uuid: str
    fecha: datetime
    operation_type: str
    status: str
    sucursal_id: int | None = None
    reason: str | None = None
    refund_id: int | None = None
    refund_status: str | None = None


class SyncMetricasResponse(BaseModel):
    empresa_id: int | None
    total_operaciones: int
    total_confirmadas: int
    total_conflictos: int
    total_rechazadas: int
    total_procesando: int
    tasa_exito_porcentaje: float
    operaciones_por_tipo: dict[str, int]
    reembolsos_asociados: dict[str, Any]
    conflictos_recientes: list[SyncDiagnosticoItem]

