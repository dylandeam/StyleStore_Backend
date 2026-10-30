"""Schemas for configurable subscription plans."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


PLAN_CODES = {"basico", "intermedio", "profesional"}


def normalize_plan_code(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "-")
    if not normalized or len(normalized) > 30:
        raise ValueError("El código del plan debe tener entre 1 y 30 caracteres.")
    if not all(character.isalnum() or character in {"-", "_"} for character in normalized):
        raise ValueError("El código solo puede contener letras, números, guiones y guiones bajos.")
    return normalized


class PlanUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=80)
    descripcion: str | None = Field(None, max_length=1200)
    precio_mensual: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=12, decimal_places=2)
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


class PlanCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=30)
    nombre: str = Field(..., min_length=2, max_length=80)
    descripcion: str | None = Field(None, max_length=1200)
    precio_mensual: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), max_digits=12, decimal_places=2)
    moneda: str = Field(default="BOB", min_length=3, max_length=3)
    max_sucursales: int | None = Field(default=None, ge=1, le=10000)
    ia_generativa: bool = False
    beneficios: list[str] = Field(default_factory=list, max_length=30)
    capacidades: dict[str, bool] = Field(default_factory=dict)
    estilo: dict[str, Any] = Field(default_factory=dict)
    active: bool = True

    @field_validator("codigo")
    @classmethod
    def valid_code(cls, value: str):
        return normalize_plan_code(value)

    @field_validator("moneda")
    @classmethod
    def normalize_currency(cls, value: str):
        return value.upper()

    @field_validator("beneficios")
    @classmethod
    def clean_benefits(cls, value: list[str]):
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
    pago_confirmado: bool = False
    referencia_pago: str | None = Field(None, min_length=3, max_length=120)

    @field_validator("plan_codigo")
    @classmethod
    def valid_plan_code(cls, value: str):
        return normalize_plan_code(value)


class ContratacionPayPalCreate(BaseModel):
    plan_codigo: str
    return_url: str | None = Field(None, max_length=500)
    cancel_url: str | None = Field(None, max_length=500)

    @field_validator("plan_codigo")
    @classmethod
    def valid_plan_code(cls, value: str):
        return normalize_plan_code(value)


class ContratacionPayPalCapture(BaseModel):
    paypal_order_id: str = Field(..., min_length=3, max_length=120)


class ContratacionResponse(BaseModel):
    id: int
    plan_codigo: str
    plan_nombre: str
    estado: str
    estado_pago: str
    referencia_pago: str | None
    pagado_en: datetime | None
    precio: Decimal
    moneda: str
    fecha_inicio: date
    fecha_fin: date | None
    created_at: datetime
    max_sucursales: int | None = None
    capacidades: dict[str, bool] | None = None
