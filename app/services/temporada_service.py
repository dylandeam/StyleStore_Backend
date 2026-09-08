"""
Service para gestión de Temporadas (CU14).
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.temporada import Temporada
from app.models.producto import Producto
from app.models.user import User
from app.schemas.temporada import TemporadaCreate, TemporadaUpdate, TemporadaResponse
from app.services.bitacora_service import BitacoraService


class TemporadaService:
    def __init__(self, db: Session):
        self.db = db
        self.bitacora = BitacoraService(db)

    def list_temporadas(self) -> list[TemporadaResponse]:
        temps = self.db.query(Temporada).order_by(Temporada.nombre.asc()).all()
        return [TemporadaResponse.model_validate(t) for t in temps]

    def get_temporada_by_id(self, temp_id: int) -> TemporadaResponse:
        t = self.db.query(Temporada).filter(Temporada.id == temp_id).first()
        if not t:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Temporada con ID {temp_id} no encontrada.",
            )
        return TemporadaResponse.model_validate(t)

    def create_temporada(self, req: TemporadaCreate, current_user: User | None = None) -> TemporadaResponse:
        nombre_clean = req.nombre.strip()
        if self.db.query(Temporada).filter(Temporada.nombre.ilike(nombre_clean)).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una temporada con el nombre '{nombre_clean}'.",
            )
        t = Temporada(nombre=nombre_clean)
        self.db.add(t)
        self.db.commit()
        self.db.refresh(t)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Creó temporada '{t.nombre}'",
                module="temporadas",
            )
        return TemporadaResponse.model_validate(t)

    def update_temporada(self, temp_id: int, req: TemporadaUpdate, current_user: User | None = None) -> TemporadaResponse:
        t = self.db.query(Temporada).filter(Temporada.id == temp_id).first()
        if not t:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Temporada con ID {temp_id} no encontrada.",
            )
        nombre_clean = req.nombre.strip()
        existente = (
            self.db.query(Temporada)
            .filter(Temporada.nombre.ilike(nombre_clean), Temporada.id != temp_id)
            .first()
        )
        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe otra temporada con el nombre '{nombre_clean}'.",
            )
        t.nombre = nombre_clean
        self.db.commit()
        self.db.refresh(t)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Actualizó temporada ID {t.id} a '{t.nombre}'",
                module="temporadas",
            )
        return TemporadaResponse.model_validate(t)

    def delete_temporada(self, temp_id: int, current_user: User | None = None) -> dict:
        t = self.db.query(Temporada).filter(Temporada.id == temp_id).first()
        if not t:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Temporada con ID {temp_id} no encontrada.",
            )
        tiene_prods = self.db.query(Producto).filter(Producto.temporada_id == temp_id).first()
        if tiene_prods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar la temporada porque tiene productos asociados.",
            )

        nombre = t.nombre
        self.db.delete(t)
        self.db.commit()

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Eliminó temporada '{nombre}'",
                module="temporadas",
            )
        return {"message": f"Temporada '{nombre}' eliminada exitosamente."}
