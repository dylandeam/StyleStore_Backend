"""Pydantic schemas for SaaS companies (tenants)."""
from datetime import date, datetime
import re
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class EmpresaCreate(BaseModel):
    codigo: str = Field(..., min_length=2, max_length=50)
    nombre: str = Field(..., min_length=2, max_length=150)
    admin_email: EmailStr
    admin_name: str = Field(..., min_length=2, max_length=100)
    admin_password: str = Field(..., min_length=8, max_length=100)
    plan_codigo: Literal["basico", "intermedio", "profesional"] = "basico"

    @field_validator("codigo")
    @classmethod
    def validate_codigo(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", normalized):
            raise ValueError("El código solo admite letras minúsculas, números, guion y guion bajo.")
        return normalized

    @field_validator("admin_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[a-z]", value) or not re.search(r"[A-Z]", value) or not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("La contraseña debe incluir mayúscula, minúscula y carácter especial.")
        return value


class EmpresaResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    active: bool
    inactive_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmpresaPublicResponse(BaseModel):
    codigo: str
    nombre: str

    model_config = {"from_attributes": True}


class EmpresaConAdminResponse(EmpresaResponse):
    admin_user_id: int


class EmpresaUpdate(BaseModel):
    codigo: str | None = Field(None, min_length=2, max_length=50)
    nombre: str | None = Field(None, min_length=2, max_length=150)

    @field_validator("codigo")
    @classmethod
    def validate_codigo(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", normalized):
            raise ValueError("El código solo admite letras minúsculas, números, guion y guion bajo.")
        return normalized


class EmpresaEstadoUpdate(BaseModel):
    active: bool


class TenantAdminUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = Field(None, min_length=2, max_length=100)
    password: str | None = Field(None, min_length=8, max_length=100)
    is_active: bool | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        if value is not None and (
            not re.search(r"[a-z]", value)
            or not re.search(r"[A-Z]", value)
            or not re.search(r"[^A-Za-z0-9]", value)
        ):
            raise ValueError("La contraseña debe incluir mayúscula, minúscula y carácter especial.")
        return value


class TenantAdminResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EmpresaSuscripcionUpdate(BaseModel):
    plan_codigo: Literal["basico", "intermedio", "profesional"]
    estado: Literal["activa", "suspendida", "vencida", "cancelada"] = "activa"
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    pago_confirmado: bool = True
    referencia_pago: str | None = Field(default=None, min_length=3, max_length=120)


class EmpresaSuscripcionResponse(BaseModel):
    id: int
    plan_codigo: str
    plan_nombre: str
    estado: str
    estado_pago: str
    referencia_pago: str | None = None
    pagado_en: datetime | None = None
    precio: float
    moneda: str
    fecha_inicio: date
    fecha_fin: date | None
    max_sucursales: int | None = None


class TenantBranchSummary(BaseModel):
    id: int
    nombre: str
    ciudad: str
    active: bool


class TenantUserSummary(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    rol: str
    active: bool


class TenantCapacidadesResponse(BaseModel):
    chatbot: bool = False
    predicciones: bool = False
    max_sucursales: int | None = None
    cupo_sucursales_disponible: int | None = None


class EmpresaResumenResponse(EmpresaResponse):
    admin: TenantAdminResponse | None = None
    suscripcion: EmpresaSuscripcionResponse | None = None
    usuarios_count: int = 0
    sucursales_count: int = 0
    archivos_count: int = 0
    proximamente_count: int = 0
    pruebas_virtuales_count: int = 0
    capacidades: TenantCapacidadesResponse | None = None
    sucursales: list[TenantBranchSummary] = []
    usuarios: list[TenantUserSummary] = []
