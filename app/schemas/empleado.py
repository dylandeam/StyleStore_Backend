"""
Pydantic schemas para Empleados (CU8).
"""
from datetime import datetime, time
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


DiaSemana = Literal[
    "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"
]


class EmpleadoSucursalInput(BaseModel):
    sucursal_id: int = Field(..., gt=0)
    hora_inicio: time
    hora_fin: time
    dias_semana: list[DiaSemana] = Field(..., min_length=1)

    @field_validator("dias_semana")
    @classmethod
    def unique_days(cls, value: list[DiaSemana]):
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def valid_time_range(self):
        if self.hora_inicio >= self.hora_fin:
            raise ValueError("La hora de inicio debe ser anterior a la hora de fin.")
        return self


class EmpleadoSucursalResponse(EmpleadoSucursalInput):
    id: int
    sucursal_nombre: str | None = None


class EmpleadoCreate(BaseModel):
    """Schema para registrar empleado junto con su cuenta de usuario."""

    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str = Field(..., min_length=2, max_length=100)
    ci: str = Field(..., min_length=4, max_length=20)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field(default="encargado_sucursal")

    sucursal_id: int
    edad: int = Field(..., ge=18, le=100)
    sueldo: Decimal = Field(..., ge=Decimal("0"))
    telefono: str = Field(..., min_length=5, max_length=20)
    direccion: str = Field(..., min_length=3, max_length=255)
    foto: str | None = None
    jornada_tipo: Literal["tiempo_completo", "medio_tiempo"] = "tiempo_completo"
    asignaciones: list[EmpleadoSucursalInput] | None = None


class EmpleadoUpdate(BaseModel):
    """Schema para actualizar datos de empleado."""

    nombre: str | None = None
    apellido: str | None = None
    ci: str | None = None
    role: str | None = None
    sucursal_id: int | None = None
    edad: int | None = Field(None, ge=18, le=100)
    sueldo: Decimal | None = Field(None, ge=Decimal("0"))
    telefono: str | None = None
    direccion: str | None = None
    foto: str | None = None
    jornada_tipo: Literal["tiempo_completo", "medio_tiempo"] | None = None
    asignaciones: list[EmpleadoSucursalInput] | None = None


class EmpleadoResponse(BaseModel):
    """Schema para exponer empleado en la API."""

    codigo: str
    user_id: int
    sucursal_id: int
    edad: int
    sueldo: Decimal
    telefono: str
    direccion: str
    foto: str | None = None
    jornada_tipo: Literal["tiempo_completo", "medio_tiempo"]
    asignaciones: list[EmpleadoSucursalResponse] = Field(default_factory=list)

    # Datos del usuario asociado
    nombre: str | None = None
    apellido: str | None = None
    ci: str | None = None
    email: str | None = None
    role: str | None = None
    sucursal_nombre: str | None = None
    empresa_id: int | None = None
    empresa_nombre: str | None = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
