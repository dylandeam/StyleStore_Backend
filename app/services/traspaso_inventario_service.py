"""Flujo transaccional de traspasos entre sucursales."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.bitacora import Bitacora
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.stock_inventario import StockInventario
from app.models.talla import Talla
from app.models.traspaso_inventario import TraspasoInventario
from app.models.user import User
from app.schemas.traspaso_inventario import TraspasoCreateRequest
from app.services.tenant_scope import get_scoped_sucursal


class TraspasoInventarioService:
    def __init__(self, db: Session):
        self.db = db

    def _tenant_id(self, user: User) -> int:
        if user.empresa_id is None:
            raise BadRequestException("El usuario debe pertenecer a una empresa para gestionar traspasos.")
        return user.empresa_id

    def _get_scoped(self, traspaso_id: int, user: User, lock: bool = False) -> TraspasoInventario:
        query = self.db.query(TraspasoInventario).filter(TraspasoInventario.id == traspaso_id)
        if not user.is_platform_admin:
            query = query.filter(TraspasoInventario.empresa_id == self._tenant_id(user))
        if lock:
            query = query.with_for_update(of=TraspasoInventario)
        item = query.first()
        if not item:
            raise NotFoundException("Traspaso de inventario no encontrado.")
        return item

    @staticmethod
    def _same_payload(item: TraspasoInventario, payload: TraspasoCreateRequest) -> bool:
        return all((
            item.sucursal_origen_id == payload.sucursal_origen_id,
            item.sucursal_destino_id == payload.sucursal_destino_id,
            item.producto_color_id == payload.producto_color_id,
            item.talla_id == payload.talla_id,
            item.cantidad == payload.cantidad,
        ))

    def _audit(self, user: User, action: str) -> None:
        self.db.add(Bitacora(
            empresa_id=user.empresa_id,
            user_id=user.id,
            user_snapshot=f"{user.name} ({user.email})",
            action=action,
            module="inventario",
            ip_address="127.0.0.1",
        ))

    def create(self, payload: TraspasoCreateRequest, user: User) -> TraspasoInventario:
        empresa_id = self._tenant_id(user)
        if payload.sucursal_origen_id == payload.sucursal_destino_id:
            raise BadRequestException("Las sucursales de origen y destino deben ser distintas.")

        existing = self.db.query(TraspasoInventario).filter(
            TraspasoInventario.empresa_id == empresa_id,
            TraspasoInventario.idempotency_key == payload.idempotency_key,
        ).first()
        if existing:
            if not self._same_payload(existing, payload):
                raise ConflictException("La clave de idempotencia ya fue usada con otros datos.")
            return existing

        get_scoped_sucursal(self.db, user, payload.sucursal_origen_id)
        get_scoped_sucursal(self.db, user, payload.sucursal_destino_id)
        variant = (
            self.db.query(ProductoColor)
            .join(Producto, Producto.codigo == ProductoColor.producto_codigo)
            .filter(ProductoColor.id == payload.producto_color_id, Producto.empresa_id == empresa_id)
            .first()
        )
        if not variant:
            raise NotFoundException("Variante de producto no encontrada.")
        if not self.db.query(Talla).filter(Talla.id == payload.talla_id, Talla.empresa_id == empresa_id).first():
            raise NotFoundException("Talla no encontrada.")

        source = self.db.query(StockInventario).filter(
            StockInventario.producto_color_id == payload.producto_color_id,
            StockInventario.talla_id == payload.talla_id,
            StockInventario.sucursal_id == payload.sucursal_origen_id,
        ).first()
        if not source:
            raise NotFoundException("No existe stock de esa variante en la sucursal de origen.")
        if source.cantidad < payload.cantidad:
            raise ConflictException("El stock de origen es insuficiente para solicitar el traspaso.")

        item = TraspasoInventario(
            empresa_id=empresa_id,
            sucursal_origen_id=payload.sucursal_origen_id,
            sucursal_destino_id=payload.sucursal_destino_id,
            producto_color_id=payload.producto_color_id,
            talla_id=payload.talla_id,
            cantidad=payload.cantidad,
            idempotency_key=payload.idempotency_key,
            observacion=payload.observacion,
            solicitado_por_id=user.id,
        )
        self.db.add(item)
        self.db.flush()
        self._audit(user, f"Solicitó traspaso de inventario #{item.id} por {item.cantidad} unidades")
        self.db.commit()
        self.db.refresh(item)
        return item

    def list(self, user: User, estado: str | None = None) -> list[TraspasoInventario]:
        query = self.db.query(TraspasoInventario)
        if not user.is_platform_admin:
            query = query.filter(TraspasoInventario.empresa_id == self._tenant_id(user))
        if estado:
            query = query.filter(TraspasoInventario.estado == estado)
        return query.order_by(TraspasoInventario.created_at.desc(), TraspasoInventario.id.desc()).all()

    def approve(self, traspaso_id: int, respuesta: str | None, user: User) -> TraspasoInventario:
        item = self._get_scoped(traspaso_id, user, lock=True)
        if item.estado == "aprobado":
            return item
        if item.estado != "pendiente":
            raise ConflictException(f"No se puede aprobar un traspaso en estado '{item.estado}'.")

        rows = (
            self.db.query(StockInventario)
            .filter(
                StockInventario.producto_color_id == item.producto_color_id,
                StockInventario.talla_id == item.talla_id,
                StockInventario.sucursal_id.in_([item.sucursal_origen_id, item.sucursal_destino_id]),
            )
            .order_by(StockInventario.id)
            .with_for_update(of=StockInventario)
            .all()
        )
        source = next((row for row in rows if row.sucursal_id == item.sucursal_origen_id), None)
        destination = next((row for row in rows if row.sucursal_id == item.sucursal_destino_id), None)
        if not source or source.cantidad < item.cantidad:
            raise ConflictException("El stock de origen ya no es suficiente para aprobar el traspaso.")

        source.cantidad -= item.cantidad
        if destination:
            destination.cantidad += item.cantidad
        else:
            destination = StockInventario(
                producto_color_id=item.producto_color_id,
                talla_id=item.talla_id,
                sucursal_id=item.sucursal_destino_id,
                cantidad=item.cantidad,
                precio_variante=source.precio_variante,
                medidas=dict(source.medidas or {}),
            )
            self.db.add(destination)

        item.estado = "aprobado"
        item.respuesta = respuesta
        item.procesado_por_id = user.id
        item.procesado_en = datetime.now(timezone.utc)
        self._audit(user, f"Aprobó traspaso de inventario #{item.id}; movió {item.cantidad} unidades")
        self.db.commit()
        self.db.refresh(item)
        return item

    def decide_without_movement(
        self, traspaso_id: int, estado: str, respuesta: str | None, user: User
    ) -> TraspasoInventario:
        item = self._get_scoped(traspaso_id, user, lock=True)
        if item.estado == estado:
            return item
        if item.estado != "pendiente":
            raise ConflictException(f"No se puede cambiar un traspaso en estado '{item.estado}'.")
        item.estado = estado
        item.respuesta = respuesta
        item.procesado_por_id = user.id
        item.procesado_en = datetime.now(timezone.utc)
        verbo = "Rechazó" if estado == "rechazado" else "Canceló"
        self._audit(user, f"{verbo} traspaso de inventario #{item.id}")
        self.db.commit()
        self.db.refresh(item)
        return item

    @staticmethod
    def serialize(item: TraspasoInventario) -> dict:
        product = item.producto_color.producto if item.producto_color else None
        color = item.producto_color.color if item.producto_color else None
        return {
            "id": item.id,
            "empresa_id": item.empresa_id,
            "sucursal_origen_id": item.sucursal_origen_id,
            "sucursal_origen": item.sucursal_origen.name,
            "sucursal_destino_id": item.sucursal_destino_id,
            "sucursal_destino": item.sucursal_destino.name,
            "producto_color_id": item.producto_color_id,
            "producto_codigo": product.codigo if product else "",
            "producto_nombre": product.nombre if product else "",
            "color": color.nombre if color else "",
            "talla_id": item.talla_id,
            "talla": item.talla.nombre if item.talla else "",
            "cantidad": item.cantidad,
            "estado": item.estado,
            "idempotency_key": item.idempotency_key,
            "observacion": item.observacion,
            "respuesta": item.respuesta,
            "solicitado_por": item.solicitado_por.name,
            "procesado_por": item.procesado_por.name if item.procesado_por else None,
            "created_at": item.created_at,
            "procesado_en": item.procesado_en,
        }
