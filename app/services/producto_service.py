"""
Service para gestión de Productos (CU10) y Catálogo (CU17).
Conforme a Especificación StyleStore v4 (Diagrama DB Oficial).
PK: codigo (String(50)).
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.color import Color
from app.models.categoria import Categoria
from app.models.temporada import Temporada
from app.models.stock_inventario import StockInventario
from app.models.user import User
from app.schemas.producto import ProductoCreate, ProductoUpdate, ProductoResponse
from app.schemas.color import ColorResponse
from app.services.bitacora_service import BitacoraService


class ProductoService:
    def __init__(self, db: Session):
        self.db = db
        self.bitacora = BitacoraService(db)

    def _generar_codigo_siguiente(self) -> str:
        """Autogenera código PROD-0001 incremental como fallback si no se especifica."""
        count = self.db.query(Producto).count()
        candidate = f"PROD-{count + 1:04d}"
        while self.db.query(Producto).filter(Producto.codigo == candidate).first():
            count += 1
            candidate = f"PROD-{count + 1:04d}"
        return candidate

    def _to_response(self, prod: Producto) -> ProductoResponse:
        # Extraer colores asociados
        colores_resp = []
        for pc in prod.colores_rel:
            if pc.color:
                colores_resp.append(ColorResponse.model_validate(pc.color))

        # Calcular stock total sumando inventarios
        pc_ids = [pc.id for pc in prod.colores_rel]
        total_stock = 0
        if pc_ids:
            sum_res = (
                self.db.query(func.sum(StockInventario.cantidad))
                .filter(StockInventario.producto_color_id.in_(pc_ids))
                .scalar()
            )
            total_stock = int(sum_res or 0)

        return ProductoResponse(
            codigo=prod.codigo,
            nombre=prod.nombre,
            descripcion=prod.descripcion,
            foto=prod.foto,
            precio=prod.precio,
            categoria_id=prod.categoria_id,
            categoria_nombre=prod.categoria.nombre if prod.categoria else None,
            temporada_id=prod.temporada_id,
            temporada_nombre=prod.temporada.nombre if prod.temporada else None,
            active=prod.active,
            colores=colores_resp,
            stock_total=total_stock,
            created_at=prod.created_at,
            updated_at=prod.updated_at,
        )

    def list_productos(
        self,
        active_only: bool = False,
        categoria_id: int | None = None,
        temporada_id: int | None = None,
    ) -> list[ProductoResponse]:
        query = self.db.query(Producto)
        if active_only:
            query = query.filter(Producto.active.is_(True))
        if categoria_id:
            query = query.filter(Producto.categoria_id == categoria_id)
        if temporada_id:
            query = query.filter(Producto.temporada_id == temporada_id)

        prods = query.order_by(Producto.nombre.asc()).all()
        return [self._to_response(p) for p in prods]

    def get_producto_by_codigo(self, codigo: str) -> ProductoResponse:
        prod = self.db.query(Producto).filter(Producto.codigo == codigo).first()
        if not prod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con código '{codigo}' no encontrado.",
            )
        return self._to_response(prod)

    def create_producto(self, req: ProductoCreate, current_user: User | None = None) -> ProductoResponse:
        # Validar categoria y temporada
        if not self.db.query(Categoria).filter(Categoria.id == req.categoria_id).first():
            raise HTTPException(status_code=404, detail=f"Categoría ID {req.categoria_id} no existe.")
        if not self.db.query(Temporada).filter(Temporada.id == req.temporada_id).first():
            raise HTTPException(status_code=404, detail=f"Temporada ID {req.temporada_id} no existe.")

        codigo = req.codigo.strip() if req.codigo and req.codigo.strip() else self._generar_codigo_siguiente()
        if self.db.query(Producto).filter(Producto.codigo == codigo).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un producto con el código '{codigo}'.",
            )

        prod = Producto(
            codigo=codigo,
            nombre=req.nombre.strip(),
            descripcion=req.descripcion,
            foto=req.foto,
            precio=req.precio,
            categoria_id=req.categoria_id,
            temporada_id=req.temporada_id,
            active=req.active,
        )
        self.db.add(prod)
        self.db.flush()

        # Asignar colores habilitados
        if req.color_ids:
            for c_id in set(req.color_ids):
                if self.db.query(Color).filter(Color.id == c_id).first():
                    pc = ProductoColor(producto_codigo=prod.codigo, color_id=c_id)
                    self.db.add(pc)

        self.db.commit()
        self.db.refresh(prod)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Creó producto '{prod.codigo}' - {prod.nombre}",
                module="productos",
            )

        return self._to_response(prod)

    def update_producto(
        self, codigo: str, req: ProductoUpdate, current_user: User | None = None
    ) -> ProductoResponse:
        prod = self.db.query(Producto).filter(Producto.codigo == codigo).first()
        if not prod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con código '{codigo}' no encontrado.",
            )

        if req.categoria_id is not None:
            if not self.db.query(Categoria).filter(Categoria.id == req.categoria_id).first():
                raise HTTPException(status_code=404, detail=f"Categoría ID {req.categoria_id} no existe.")
            prod.categoria_id = req.categoria_id

        if req.temporada_id is not None:
            if not self.db.query(Temporada).filter(Temporada.id == req.temporada_id).first():
                raise HTTPException(status_code=404, detail=f"Temporada ID {req.temporada_id} no existe.")
            prod.temporada_id = req.temporada_id

        if req.nombre is not None:
            prod.nombre = req.nombre.strip()
        if req.descripcion is not None:
            prod.descripcion = req.descripcion
        if req.foto is not None:
            prod.foto = req.foto
        if req.precio is not None:
            prod.precio = req.precio
        if req.active is not None:
            prod.active = req.active

        # Sincronizar colores si se envían
        if req.color_ids is not None:
            existing_pcs = {pc.color_id: pc for pc in prod.colores_rel}
            new_color_ids = set(req.color_ids)

            # Eliminar los que ya no están (si no tienen stock)
            for cid, pc in list(existing_pcs.items()):
                if cid not in new_color_ids:
                    # Validar si tiene stock
                    tiene_stock = self.db.query(StockInventario).filter(StockInventario.producto_color_id == pc.id).first()
                    if tiene_stock:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"No se puede remover el color ID {cid} porque tiene existencias en inventario.",
                        )
                    self.db.delete(pc)

            # Agregar nuevos
            for cid in new_color_ids:
                if cid not in existing_pcs and self.db.query(Color).filter(Color.id == cid).first():
                    new_pc = ProductoColor(producto_codigo=prod.codigo, color_id=cid)
                    self.db.add(new_pc)

        self.db.commit()
        self.db.refresh(prod)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Actualizó producto '{prod.codigo}'",
                module="productos",
            )

        return self._to_response(prod)

    def delete_producto(self, codigo: str, current_user: User | None = None) -> dict:
        prod = self.db.query(Producto).filter(Producto.codigo == codigo).first()
        if not prod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con código '{codigo}' no encontrado.",
            )

        nombre = prod.nombre
        self.db.delete(prod)
        self.db.commit()

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Eliminó producto '{codigo}' - {nombre}",
                module="productos",
            )

        return {"message": f"Producto '{codigo}' eliminado exitosamente."}
