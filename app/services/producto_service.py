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
from app.models.coleccion import Coleccion
from app.models.stock_inventario import StockInventario
from app.models.user import User
from app.schemas.producto import ProductoCreate, ProductoUpdate, ProductoResponse, PromocionUpdate
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

    def _to_response(self, prod: Producto, sucursal_id: int | None = None) -> ProductoResponse:
        # Extraer colores asociados
        colores_resp = []
        for pc in prod.colores_rel:
            if pc.color:
                colores_resp.append(ColorResponse.model_validate(pc.color))

        # Calcular stock total sumando inventarios (opcionalmente filtrado por sucursal)
        pc_ids = [pc.id for pc in prod.colores_rel]
        total_stock = 0
        if pc_ids:
            stock_q = self.db.query(func.sum(StockInventario.cantidad)).filter(
                StockInventario.producto_color_id.in_(pc_ids)
            )
            if sucursal_id is not None:
                stock_q = stock_q.filter(StockInventario.sucursal_id == sucursal_id)
            sum_res = stock_q.scalar()
            total_stock = int(sum_res or 0)

        # Promoción y Descuentos
        en_promocion = getattr(prod, "en_promocion", False) or False
        porcentaje_descuento = getattr(prod, "porcentaje_descuento", 0) or 0
        titulo_promocion = getattr(prod, "titulo_promocion", None)
        precio_descuento = getattr(prod, "precio_descuento", None)
        if en_promocion and porcentaje_descuento > 0 and prod.precio:
            from decimal import Decimal
            desc = (prod.precio * Decimal(porcentaje_descuento)) / Decimal(100)
            precio_descuento = round(prod.precio - desc, 2)

        return ProductoResponse(
            codigo=prod.codigo,
            nombre=prod.nombre,
            descripcion=prod.descripcion,
            foto=prod.foto,
            foto_trasera=getattr(prod, "foto_trasera", None),
            foto_vestidor_frontal=getattr(prod, "foto_vestidor_frontal", None),
            foto_vestidor_trasera=getattr(prod, "foto_vestidor_trasera", None),
            tipo_prenda=getattr(prod, "tipo_prenda", "superior") or "superior",
            puntos_clave_ia=getattr(prod, "puntos_clave_ia", None),
            precio=prod.precio,
            categoria_id=prod.categoria_id,
            categoria_nombre=prod.categoria.nombre if prod.categoria else None,
            temporada_id=prod.temporada_id,
            temporada_nombre=prod.temporada.nombre if prod.temporada else None,
            coleccion_id=prod.coleccion_id,
            coleccion_nombre=prod.coleccion.nombre if prod.coleccion else None,
            active=prod.active,
            visible_en_catalogo=prod.visible_en_catalogo,
            en_promocion=en_promocion,
            porcentaje_descuento=porcentaje_descuento,
            precio_descuento=precio_descuento,
            titulo_promocion=titulo_promocion,
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
        coleccion_id: int | None = None,
        sucursal_id: int | None = None,
        search: str | None = None,
    ) -> list[ProductoResponse]:
        query = self.db.query(Producto)
        if active_only:
            query = query.filter(Producto.active.is_(True))
        if categoria_id:
            query = query.filter(Producto.categoria_id == categoria_id)
        if temporada_id:
            query = query.filter(Producto.temporada_id == temporada_id)
        if coleccion_id:
            query = query.filter(Producto.coleccion_id == coleccion_id)
        if search:
            query = query.filter(
                (Producto.nombre.ilike(f"%{search}%"))
                | (Producto.descripcion.ilike(f"%{search}%"))
                | (Producto.codigo.ilike(f"%{search}%"))
            )

        prods = query.order_by(Producto.nombre.asc()).all()
        return [self._to_response(p, sucursal_id=sucursal_id) for p in prods]

    def list_promociones(self, solo_en_promocion: bool = True) -> list[ProductoResponse]:
        query = self.db.query(Producto).filter(Producto.active.is_(True))
        if solo_en_promocion:
            query = query.filter(Producto.en_promocion.is_(True))
        prods = query.order_by(Producto.nombre.asc()).all()
        return [self._to_response(p) for p in prods]

    def update_promocion(
        self, codigo: str, req: PromocionUpdate, current_user: User | None = None
    ) -> ProductoResponse:
        from decimal import Decimal
        prod = self.db.query(Producto).filter(Producto.codigo == codigo).first()
        if not prod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con código '{codigo}' no encontrado.",
            )

        prod.en_promocion = req.en_promocion
        prod.porcentaje_descuento = req.porcentaje_descuento if req.en_promocion else 0
        prod.titulo_promocion = req.titulo_promocion.strip() if req.en_promocion and req.titulo_promocion else None

        if prod.en_promocion and prod.porcentaje_descuento > 0 and prod.precio:
            desc = (prod.precio * Decimal(prod.porcentaje_descuento)) / Decimal(100)
            prod.precio_descuento = round(prod.precio - desc, 2)
        else:
            prod.precio_descuento = None

        self.db.commit()
        self.db.refresh(prod)

        if current_user:
            estado_str = f"Promoción {prod.porcentaje_descuento}% OFF ({prod.titulo_promocion or 'Oferta Especial'})" if prod.en_promocion else "Promoción desactivada"
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Actualizó promoción de producto '{prod.codigo}': {estado_str}",
                module="promociones",
            )

        return self._to_response(prod)

    def get_producto_by_codigo(self, codigo: str) -> ProductoResponse:
        prod = self.db.query(Producto).filter(Producto.codigo == codigo).first()
        if not prod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con código '{codigo}' no encontrado.",
            )
        return self._to_response(prod)

    def create_producto(self, req: ProductoCreate, current_user: User | None = None) -> ProductoResponse:
        # Validar categoria, temporada y coleccion
        if not self.db.query(Categoria).filter(Categoria.id == req.categoria_id).first():
            raise HTTPException(status_code=404, detail=f"Categoría ID {req.categoria_id} no existe.")
        if not self.db.query(Temporada).filter(Temporada.id == req.temporada_id).first():
            raise HTTPException(status_code=404, detail=f"Temporada ID {req.temporada_id} no existe.")
        if req.coleccion_id is not None and not self.db.query(Coleccion).filter(Coleccion.id == req.coleccion_id).first():
            raise HTTPException(status_code=404, detail=f"Colección ID {req.coleccion_id} no existe.")

        codigo = req.codigo.strip() if req.codigo and req.codigo.strip() else self._generar_codigo_siguiente()
        if self.db.query(Producto).filter(Producto.codigo == codigo).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un producto con el código '{codigo}'.",
            )

        # Calcular precio descuento inicial si aplica
        precio_desc = req.precio_descuento
        if req.en_promocion and req.porcentaje_descuento > 0 and req.precio:
            from decimal import Decimal
            desc = (req.precio * Decimal(req.porcentaje_descuento)) / Decimal(100)
            precio_desc = round(req.precio - desc, 2)

        prod = Producto(
            codigo=codigo,
            nombre=req.nombre.strip(),
            descripcion=req.descripcion,
            foto=req.foto,
            foto_trasera=req.foto_trasera,
            foto_vestidor_frontal=req.foto_vestidor_frontal,
            foto_vestidor_trasera=req.foto_vestidor_trasera,
            tipo_prenda=req.tipo_prenda or "superior",
            puntos_clave_ia=req.puntos_clave_ia,
            precio=req.precio,
            categoria_id=req.categoria_id,
            temporada_id=req.temporada_id,
            coleccion_id=req.coleccion_id,
            active=req.active,
            visible_en_catalogo=req.visible_en_catalogo,
            en_promocion=req.en_promocion,
            porcentaje_descuento=req.porcentaje_descuento,
            precio_descuento=precio_desc,
            titulo_promocion=req.titulo_promocion,
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

        if req.coleccion_id is not None:
            if not self.db.query(Coleccion).filter(Coleccion.id == req.coleccion_id).first():
                raise HTTPException(status_code=404, detail=f"Colección ID {req.coleccion_id} no existe.")
            prod.coleccion_id = req.coleccion_id

        if req.nombre is not None:
            prod.nombre = req.nombre.strip()
        if req.descripcion is not None:
            prod.descripcion = req.descripcion
        if req.foto is not None:
            prod.foto = req.foto
        if req.foto_trasera is not None:
            prod.foto_trasera = req.foto_trasera
        if req.foto_vestidor_frontal is not None:
            prod.foto_vestidor_frontal = req.foto_vestidor_frontal
        if req.foto_vestidor_trasera is not None:
            prod.foto_vestidor_trasera = req.foto_vestidor_trasera
        if req.tipo_prenda is not None:
            prod.tipo_prenda = req.tipo_prenda
        if req.puntos_clave_ia is not None:
            prod.puntos_clave_ia = req.puntos_clave_ia
        if req.precio is not None:
            prod.precio = req.precio
        if req.active is not None:
            prod.active = req.active
        if req.visible_en_catalogo is not None:
            prod.visible_en_catalogo = req.visible_en_catalogo
        if req.en_promocion is not None:
            prod.en_promocion = req.en_promocion
        if req.porcentaje_descuento is not None:
            prod.porcentaje_descuento = req.porcentaje_descuento
        if req.titulo_promocion is not None:
            prod.titulo_promocion = req.titulo_promocion

        # Recalcular precio_descuento
        if prod.en_promocion and prod.porcentaje_descuento > 0 and prod.precio:
            from decimal import Decimal
            desc = (prod.precio * Decimal(prod.porcentaje_descuento)) / Decimal(100)
            prod.precio_descuento = round(prod.precio - desc, 2)
        else:
            prod.precio_descuento = None

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

    def analizar_y_guardar_puntos_clave(
        self, codigo: str, current_user: User | None = None
    ) -> ProductoResponse:
        """Analiza la foto de la prenda con IA, calcula los puntos clave y los almacena."""
        import json
        import os
        from app.services.garment_ai_service import GarmentAIService

        prod = self.db.query(Producto).filter(Producto.codigo == codigo).first()
        if not prod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con código '{codigo}' no encontrado.",
            )

        img_rel_path = prod.foto_vestidor_frontal or prod.foto
        if not img_rel_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El producto no cuenta con foto frontal para analizar.",
            )

        clean_path = img_rel_path.lstrip("/")
        if not clean_path.startswith("uploads"):
            clean_path = os.path.join("uploads", clean_path)
        disk_path = os.path.join(os.getcwd(), clean_path)

        resultado = GarmentAIService.analyze_garment_image(
            disk_path, tipo_prenda=prod.tipo_prenda or "superior"
        )
        prod.puntos_clave_ia = json.dumps(resultado, ensure_ascii=False)
        self.db.commit()
        self.db.refresh(prod)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Calibró puntos anatómicos IA para prenda '{prod.codigo}' ({resultado.get('tipo_manga')})",
                module="productos",
            )

        return self._to_response(prod)
