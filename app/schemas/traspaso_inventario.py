"""Contratos HTTP para traspasos de inventario."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TraspasoCreateRequest(BaseModel):
    sucursal_origen_id: int
    sucursal_destino_id: int
    producto_color_id: int
    talla_id: int
    cantidad: int = Field(..., gt=0)
    idempotency_key: str = Field(..., min_length=8, max_length=64)
    observacion: str | None = Field(None, max_length=500)

    @field_validator("idempotency_key")
    @classmethod
    def clean_key(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("La clave de idempotencia es obligatoria.")
        return value


class TraspasoDecisionRequest(BaseModel):
    respuesta: str | None = Field(None, max_length=500)


class TraspasoResponse(BaseModel):
    id: int
    empresa_id: int
    sucursal_origen_id: int
    sucursal_origen: str
    sucursal_destino_id: int
    sucursal_destino: str
    producto_color_id: int
    producto_codigo: str
    producto_nombre: str
    color: str
    talla_id: int
    talla: str
    cantidad: int
    estado: str
    idempotency_key: str
    observacion: str | None
    respuesta: str | None
    solicitado_por: str
    procesado_por: str | None
    created_at: datetime
    procesado_en: datetime | None

