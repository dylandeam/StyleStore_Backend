"""
Service para gestión de Stock_Inventario.
Conforme a Especificación StyleStore v4.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.stock_inventario import StockInventario
from app.models.producto_color import ProductoColor
from app.models.producto import Producto
from app.models.color import Color
from app.models.talla import Talla
from app.models.sucursal import Sucursal
from app.models.user import User
from app.schemas.stock_inventario import StockBulkUpdateRequest, StockInventarioResponse
from app.services.bitacora_service import BitacoraService


class StockService:
    def __init__(self, db: Session):
        self.db = db
        self.bitacora = BitacoraService(db)

    def get_stock_by_producto(self, producto_codigo: str) -> list[StockInventarioResponse]:
        prod = self.db.query(Producto).filter(Producto.codigo == producto_codigo).first()
        if not prod:
            raise HTTPException(status_code=404, detail=f"Producto '{producto_codigo}' no existe.")

        pc_ids = [pc.id for pc in prod.colores_rel]
        if not pc_ids:
            return []

        stocks = (
            self.db.query(StockInventario)
            .filter(StockInventario.producto_color_id.in_(pc_ids))
            .all()
        )

        result = []
        for s in stocks:
            result.append(
                StockInventarioResponse(
                    id=s.id,
                    producto_codigo=producto_codigo,
                    color_id=s.producto_color.color_id if s.producto_color else 0,
                    producto_color_id=s.producto_color_id,
                    color_nombre=s.producto_color.color.nombre if s.producto_color and s.producto_color.color else "",
                    talla_id=s.talla_id,
                    talla_nombre=s.talla.nombre if s.talla else "",
                    sucursal_id=s.sucursal_id,
                    sucursal_nombre=s.sucursal.name if s.sucursal else "",
                    cantidad=s.cantidad,
                    updated_at=s.updated_at,
                )
            )
        return result

    def update_stock_bulk(
        self, producto_codigo: str, req: StockBulkUpdateRequest, current_user: User | None = None
    ) -> list[StockInventarioResponse]:
        prod = self.db.query(Producto).filter(Producto.codigo == producto_codigo).first()
        if not prod:
            raise HTTPException(status_code=404, detail=f"Producto '{producto_codigo}' no existe.")

        colores_map = {pc.color_id: pc for pc in prod.colores_rel}

        for item in req.items:
            target_color_id = item.color_id if item.color_id is not None else item.producto_color_id
            if target_color_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="Identificador de color no proporcionado (color_id).",
                )

            pc = colores_map.get(target_color_id)
            if not pc:
                # Si el color no estaba pre-asociado al producto, lo asociamos automáticamente
                color_entity = self.db.query(Color).filter(Color.id == target_color_id).first()
                if color_entity:
                    pc = ProductoColor(producto_codigo=prod.codigo, color_id=target_color_id)
                    self.db.add(pc)
                    self.db.flush()
                    colores_map[target_color_id] = pc
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"El color con ID {target_color_id} no existe en el sistema.",
                    )

            if not self.db.query(Talla).filter(Talla.id == item.talla_id).first():
                raise HTTPException(status_code=404, detail=f"Talla ID {item.talla_id} no existe.")
            if not self.db.query(Sucursal).filter(Sucursal.id == item.sucursal_id).first():
                raise HTTPException(status_code=404, detail=f"Sucursal ID {item.sucursal_id} no existe.")

            stock_row = (
                self.db.query(StockInventario)
                .filter(
                    StockInventario.producto_color_id == pc.id,
                    StockInventario.talla_id == item.talla_id,
                    StockInventario.sucursal_id == item.sucursal_id,
                )
                .first()
            )

            if stock_row:
                stock_row.cantidad = item.cantidad
            else:
                stock_row = StockInventario(
                    producto_color_id=pc.id,
                    talla_id=item.talla_id,
                    sucursal_id=item.sucursal_id,
                    cantidad=item.cantidad,
                )
                self.db.add(stock_row)

        self.db.commit()

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Actualizó existencias de stock para el producto '{producto_codigo}'",
                module="productos",
            )

        return self.get_stock_by_producto(producto_codigo)
