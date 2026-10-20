"""Schemas for configurable subscription plans."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


PLAN_CODES = {"basico", "profesional", "personalizado"}


class PlanUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=80)
    descripcion: str | None = Field(None, max_length=1200)
    precio_mensual: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    moneda: str | None = Field(None, min_length=3, max_length=3)
    max_sucursales: int | None = Field(None, ge=1, le=10000)
    ia_generativa: bool | None = None
    beneficios: list[str] | None = Field(None, max_length=30)
    capacidades: dict[str, bool] | None = None
    estilo: dict[str, Any] | None = None
    active: bool | None = None

    @field_validator("moneda")
    @classmethod
    def normalize_currency(cls, value: str | None):
        return value.upper() if value else value

    @field_validator("beneficios")
    @classmethod
    def clean_benefits(cls, value: list[str] | None):
        if value is None:
            return value
        cleaned = [item.strip() for item in value if item and item.strip()]
        if any(len(item) > 180 for item in cleaned):
            raise ValueError("Cada beneficio puede tener hasta 180 caracteres.")
        return cleaned


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int | None
    codigo: str
    nombre: str
    descripcion: str | None
    precio_mensual: Decimal
    moneda: str
    max_sucursales: int | None
    ia_generativa: bool
    beneficios: list[str]
    capacidades: dict[str, bool]
    estilo: dict[str, Any]
    active: bool
    updated_at: datetime


class ContratacionCreate(BaseModel):
    plan_codigo: str

    @field_validator("plan_codigo")
    @classmethod
    def valid_plan_code(cls, value: str):
        normalized = value.strip().lower()
        if normalized not in PLAN_CODES:
            raise ValueError("El plan debe ser basico, profesional o personalizado.")
        return normalized


class ContratacionResponse(BaseModel):
    id: int
    plan_codigo: str
    plan_nombre: str
    estado: str
    precio: Decimal
    moneda: str
    fecha_inicio: date
    fecha_fin: date | None
    created_at: datetime
