"""
Service para gestión de Colores (CU12).
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.color import Color
from app.models.producto_color import ProductoColor
from app.models.stock_inventario import StockInventario
from app.models.user import User
from app.schemas.color import ColorCreate, ColorUpdate, ColorResponse
from app.services.bitacora_service import BitacoraService


class ColorService:
    def __init__(self, db: Session):
        self.db = db
        self.bitacora = BitacoraService(db)

    def list_colores(self) -> list[ColorResponse]:
        colores = self.db.query(Color).order_by(Color.nombre.asc()).all()
        return [ColorResponse.model_validate(c) for c in colores]

    def get_color_by_id(self, color_id: int) -> ColorResponse:
        c = self.db.query(Color).filter(Color.id == color_id).first()
        if not c:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Color con ID {color_id} no encontrado.",
            )
        return ColorResponse.model_validate(c)

    def create_color(self, req: ColorCreate, current_user: User | None = None) -> ColorResponse:
        nombre_clean = req.nombre.strip()
        if self.db.query(Color).filter(Color.nombre.ilike(nombre_clean)).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un color con el nombre '{nombre_clean}'.",
            )
        c = Color(nombre=nombre_clean)
        self.db.add(c)
        self.db.commit()
        self.db.refresh(c)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Creó color '{c.nombre}'",
                module="colores",
            )
        return ColorResponse.model_validate(c)

    def update_color(self, color_id: int, req: ColorUpdate, current_user: User | None = None) -> ColorResponse:
        c = self.db.query(Color).filter(Color.id == color_id).first()
        if not c:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Color con ID {color_id} no encontrado.",
            )
        nombre_clean = req.nombre.strip()
        existente = (
            self.db.query(Color)
            .filter(Color.nombre.ilike(nombre_clean), Color.id != color_id)
            .first()
        )
        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe otro color con el nombre '{nombre_clean}'.",
            )
        c.nombre = nombre_clean
        self.db.commit()
        self.db.refresh(c)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Actualizó color ID {c.id} a '{c.nombre}'",
                module="colores",
            )
        return ColorResponse.model_validate(c)

    def delete_color(self, color_id: int, current_user: User | None = None) -> dict:
        c = self.db.query(Color).filter(Color.id == color_id).first()
        if not c:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Color con ID {color_id} no encontrado.",
            )
        # Validación v4: no tener Stock_Inventario asociado vía ProductoColor
        prod_colores = self.db.query(ProductoColor.id).filter(ProductoColor.color_id == color_id).subquery()
        tiene_stock = self.db.query(StockInventario).filter(StockInventario.producto_color_id.in_(prod_colores)).first()
        if tiene_stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar el color porque tiene existencias en el inventario.",
            )
        # También validar si está asociado a un producto
        tiene_prod = self.db.query(ProductoColor).filter(ProductoColor.color_id == color_id).first()
        if tiene_prod:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar el color porque está asignado a productos del catálogo.",
            )

        nombre = c.nombre
        self.db.delete(c)
        self.db.commit()

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Eliminó color '{nombre}'",
                module="colores",
            )
        return {"message": f"Color '{nombre}' eliminado exitosamente."}
