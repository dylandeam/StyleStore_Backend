"""Contratos del módulo de reseñas por prenda."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ResenaProductoUpsert(BaseModel):
    puntuacion: int = Field(..., ge=1, le=5)
    comentario: str = Field(..., min_length=4, max_length=1200)

    @field_validator("comentario")
    @classmethod
    def normalize_comment(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if len(cleaned) < 4:
            raise ValueError("Escribe un comentario de al menos 4 caracteres")
        return cleaned


class ResenaProductoItem(BaseModel):
    id: int
    puntuacion: int
    comentario: str
    autor_nombre: str
    autor_foto: str | None = None
    compra_verificada: bool
    es_propia: bool
    created_at: datetime
    updated_at: datetime


class ResumenResenasProducto(BaseModel):
    promedio: float
    total: int
    compras_verificadas: int
    distribucion: dict[int, int]


class ResenasProductoResponse(BaseModel):
    producto_codigo: str
    resumen: ResumenResenasProducto
    resenas: list[ResenaProductoItem]
    mi_resena: ResenaProductoItem | None = None
    puede_comentar: bool

