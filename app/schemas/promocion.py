from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class PromocionAgrupadaBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=120)
    tipo: Literal["categoria", "temporada"]
    categoria_id: int | None = None
    temporada_id: int | None = None
    porcentaje: int = Field(..., ge=1, le=90)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    active: bool = True

    @model_validator(mode="after")
    def validar_objetivo(self):
        if self.tipo == "categoria" and (not self.categoria_id or self.temporada_id):
            raise ValueError("Una promoción por categoría requiere solo categoria_id.")
        if self.tipo == "temporada" and (not self.temporada_id or self.categoria_id):
            raise ValueError("Una promoción por temporada requiere solo temporada_id.")
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio.")
        return self


class PromocionAgrupadaCreate(PromocionAgrupadaBase):
    empresa_id: int | None = None


class PromocionAgrupadaUpdate(PromocionAgrupadaBase):
    pass


class PromocionAgrupadaResponse(PromocionAgrupadaBase):
    id: int
    empresa_id: int
    categoria_nombre: str | None = None
    temporada_nombre: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class CodigoDescuentoBase(BaseModel):
    codigo: str = Field(..., min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    descripcion: str | None = Field(None, max_length=200)
    porcentaje: int = Field(..., ge=1, le=90)
    aplica_online: bool = True
    aplica_presencial: bool = True
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    max_usos: int | None = Field(None, ge=1)
    active: bool = True

    @field_validator("codigo")
    @classmethod
    def normalizar_codigo(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validar_reglas(self):
        if not self.aplica_online and not self.aplica_presencial:
            raise ValueError("El código debe estar habilitado al menos en un canal.")
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio.")
        return self


class CodigoDescuentoCreate(CodigoDescuentoBase):
    empresa_id: int | None = None


class CodigoDescuentoUpdate(CodigoDescuentoBase):
    pass


class CodigoDescuentoResponse(CodigoDescuentoBase):
    id: int
    empresa_id: int
    usos_actual: int
    created_at: datetime
    model_config = {"from_attributes": True}


class ValidarCodigoRequest(BaseModel):
    codigo: str = Field(..., min_length=2, max_length=40)
    canal: Literal["online", "presencial"]


class ValidarCodigoResponse(BaseModel):
    valido: bool
    codigo: str
    porcentaje: int
    descripcion: str | None = None


class ResumenDescuento(BaseModel):
    subtotal_original: Decimal
    descuento_promociones: Decimal
    subtotal_promocional: Decimal
    descuento_codigo: Decimal
    total: Decimal
    codigo_descuento: str | None = None
    porcentaje_codigo: int = 0
