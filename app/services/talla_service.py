"""
Service para gestión de Tallas (CU13).
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.talla import Talla
from app.models.stock_inventario import StockInventario
from app.models.user import User
from app.schemas.talla import TallaCreate, TallaUpdate, TallaResponse
from app.services.bitacora_service import BitacoraService
from app.services.tenant_scope import require_effective_empresa_id, scope_by_empresa


class TallaService:
    def __init__(self, db: Session):
        self.db = db
        self.bitacora = BitacoraService(db)

    def _query(self, current_user: User):
        return scope_by_empresa(self.db.query(Talla), current_user, Talla.empresa_id)

    def list_tallas(self, current_user: User) -> list[TallaResponse]:
        tallas = self._query(current_user).order_by(Talla.id.asc()).all()
        return [TallaResponse.model_validate(t) for t in tallas]

    def get_talla_by_id(self, talla_id: int, current_user: User) -> TallaResponse:
        t = self._query(current_user).filter(Talla.id == talla_id).first()
        if not t:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Talla con ID {talla_id} no encontrada.",
            )
        return TallaResponse.model_validate(t)

    def create_talla(self, req: TallaCreate, current_user: User) -> TallaResponse:
        empresa_id = require_effective_empresa_id(current_user)
        nombre_clean = req.nombre.strip().upper()
        if self._query(current_user).filter(Talla.nombre == nombre_clean).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una talla con el nombre '{nombre_clean}'.",
            )
        t = Talla(empresa_id=empresa_id, nombre=nombre_clean)
        self.db.add(t)
        self.db.commit()
        self.db.refresh(t)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Creó talla '{t.nombre}'",
                module="tallas",
            )
        return TallaResponse.model_validate(t)

    def update_talla(self, talla_id: int, req: TallaUpdate, current_user: User) -> TallaResponse:
        t = self._query(current_user).filter(Talla.id == talla_id).first()
        if not t:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Talla con ID {talla_id} no encontrada.",
            )
        nombre_clean = req.nombre.strip().upper()
        existente = (
            self._query(current_user)
            .filter(Talla.nombre == nombre_clean, Talla.id != talla_id)
            .first()
        )
        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe otra talla con el nombre '{nombre_clean}'.",
            )
        t.nombre = nombre_clean
        self.db.commit()
        self.db.refresh(t)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Actualizó talla ID {t.id} a '{t.nombre}'",
                module="tallas",
            )
        return TallaResponse.model_validate(t)

    def delete_talla(self, talla_id: int, current_user: User) -> dict:
        t = self._query(current_user).filter(Talla.id == talla_id).first()
        if not t:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Talla con ID {talla_id} no encontrada.",
            )
        # Validación v4: no tener Stock_Inventario asociado directamente
        tiene_stock = self.db.query(StockInventario).filter(StockInventario.talla_id == talla_id).first()
        if tiene_stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar la talla porque tiene existencias registradas en el inventario.",
            )

        nombre = t.nombre
        self.db.delete(t)
        self.db.commit()

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Eliminó talla '{nombre}'",
                module="tallas",
            )
        return {"message": f"Talla '{nombre}' eliminada exitosamente."}
