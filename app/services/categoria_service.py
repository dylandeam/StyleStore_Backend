"""
Service para gestión de Categorías (CU11).
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.user import User
from app.schemas.categoria import CategoriaCreate, CategoriaUpdate, CategoriaResponse
from app.services.bitacora_service import BitacoraService


class CategoriaService:
    def __init__(self, db: Session):
        self.db = db
        self.bitacora = BitacoraService(db)

    def list_categorias(self) -> list[CategoriaResponse]:
        cats = self.db.query(Categoria).order_by(Categoria.nombre.asc()).all()
        return [CategoriaResponse.model_validate(c) for c in cats]

    def get_categoria_by_id(self, cat_id: int) -> CategoriaResponse:
        cat = self.db.query(Categoria).filter(Categoria.id == cat_id).first()
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Categoría con ID {cat_id} no encontrada.",
            )
        return CategoriaResponse.model_validate(cat)

    def create_categoria(self, req: CategoriaCreate, current_user: User | None = None) -> CategoriaResponse:
        nombre_clean = req.nombre.strip()
        if self.db.query(Categoria).filter(Categoria.nombre.ilike(nombre_clean)).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una categoría con el nombre '{nombre_clean}'.",
            )
        cat = Categoria(nombre=nombre_clean)
        self.db.add(cat)
        self.db.commit()
        self.db.refresh(cat)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Creó categoría '{cat.nombre}'",
                module="categorias",
            )
        return CategoriaResponse.model_validate(cat)

    def update_categoria(self, cat_id: int, req: CategoriaUpdate, current_user: User | None = None) -> CategoriaResponse:
        cat = self.db.query(Categoria).filter(Categoria.id == cat_id).first()
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Categoría con ID {cat_id} no encontrada.",
            )
        nombre_clean = req.nombre.strip()
        existente = (
            self.db.query(Categoria)
            .filter(Categoria.nombre.ilike(nombre_clean), Categoria.id != cat_id)
            .first()
        )
        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe otra categoría con el nombre '{nombre_clean}'.",
            )
        cat.nombre = nombre_clean
        self.db.commit()
        self.db.refresh(cat)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Actualizó categoría ID {cat.id} a '{cat.nombre}'",
                module="categorias",
            )
        return CategoriaResponse.model_validate(cat)

    def delete_categoria(self, cat_id: int, current_user: User | None = None) -> dict:
        cat = self.db.query(Categoria).filter(Categoria.id == cat_id).first()
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Categoría con ID {cat_id} no encontrada.",
            )
        # Validación de integridad referencial
        tiene_prods = self.db.query(Producto).filter(Producto.categoria_id == cat_id).first()
        if tiene_prods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar la categoría porque tiene productos asociados.",
            )
        nombre = cat.nombre
        self.db.delete(cat)
        self.db.commit()

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Eliminó categoría '{nombre}'",
                module="categorias",
            )
        return {"message": f"Categoría '{nombre}' eliminada exitosamente."}
