"""Contratos de la API de favoritos."""
from datetime import datetime

from pydantic import BaseModel


class FavoritoResponse(BaseModel):
    id: int
    empresa_id: int
    producto_codigo: str
    created_at: datetime
    producto_nombre: str
    producto_foto: str | None = None
    precio: float
    precio_descuento: float | None = None
    en_promocion: bool = False


class FavoritoEstadoResponse(BaseModel):
    producto_codigo: str
    es_favorito: bool

