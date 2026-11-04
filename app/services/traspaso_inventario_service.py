"""Flujo transaccional de traspasos entre sucursales."""
from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, ConflictException, ForbiddenException, NotFoundException
from app.models.empleado import Empleado
from app.models.notificacion import Notificacion
from app.models.bitacora import Bitacora
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.stock_inventario import StockInventario
from app.models.talla import Talla
from app.models.traspaso_inventario import TraspasoInventario
from app.models.user import User
from app.schemas.traspaso_inventario import TraspasoCreateRequest
from app.services.notificacion_service import NotificacionService


class TraspasoInventarioService:
    def __init__(self, db: Session):
        self.db = db

    def _tenant_id(self, user: User) -> int:
        if user.empresa_id is None:
            raise BadRequestException("El usuario debe pertenecer a una empresa para gestionar traspasos.")
        return user.empresa_id

    @staticmethod
    def _role(user: User) -> str:
        return str(user.role or "").strip().lower()

    def _is_tenant_admin(self, user: User) -> bool:
        return not user.is_platform_admin and self._role(user) in {
            "administrador", "administrador_tenant", "admin_tenant"
        }

    def _is_branch_manager(self, user: User) -> bool:
        return not user.is_platform_admin and self._role(user) in {"encargado", "encargado_sucursal"}

    def _assert_can_request(self, user: User, destination_id: int) -> None:
        if self._is_tenant_admin(user):
            return
        if not self._is_branch_manager(user):
            raise ForbiddenException("Solo el administrador del tenant o un encargado de sucursal puede solicitar traspasos.")
        employee = self.db.query(Empleado).filter(Empleado.user_id == user.id).first()
        assigned = {employee.sucursal_id} if employee and employee.sucursal_id else set()
        if employee:
            assigned.update(item.sucursal_id for item in (employee.asignaciones or []))
        if destination_id not in assigned:
            raise ForbiddenException("El encargado solo puede solicitar stock para una sucursal que tenga asignada.")

    def _assert_tenant_admin(self, user: User) -> None:
        if not self._is_tenant_admin(user):
            raise ForbiddenException("Solo el administrador del tenant puede aprobar o rechazar traspasos.")

    def _notify_users(self, item: TraspasoInventario, user_ids: set[int], tipo: str, title: str, message: str) -> None:
        notifier = NotificacionService(self.db)
        action_url = f"/admin/inventario?vista=traspasos&traspaso_id={item.id}"
        for user_id in user_ids:
            exists = self.db.query(Notificacion).filter(
                Notificacion.empresa_id == item.empresa_id,
                Notificacion.user_id == user_id,
                Notificacion.tipo == tipo,
                Notificacion.url_accion == action_url,
            ).first()
            if not exists:
                notifier.crear_notificacion(
                    user_id=user_id,
                    tipo=tipo,
                    titulo=title,
                    mensaje=message,
                    url_accion=action_url,
                    enviar_email=False,
                    empresa_id=item.empresa_id,
                )

    def _tenant_admin_ids(self, empresa_id: int) -> set[int]:
        users = self.db.query(User).filter(
            User.empresa_id == empresa_id,
            User.is_active == True,
            User.is_platform_admin == False,
        ).all()
        return {user.id for user in users if self._is_tenant_admin(user)}

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
        self._assert_can_request(user, payload.sucursal_destino_id)
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

        # El encargado puede pedir reposición desde otra sucursal del mismo tenant,
        # pero solo hacia una sucursal que tenga asignada. El administrador conserva
        # la decisión final y es quien ejecuta el movimiento real.
        from app.models.sucursal import Sucursal
        branches = self.db.query(Sucursal).filter(
            Sucursal.empresa_id == empresa_id,
            Sucursal.id.in_([payload.sucursal_origen_id, payload.sucursal_destino_id]),
        ).all()
        if len(branches) != 2:
            raise NotFoundException("Una de las sucursales no pertenece al tenant activo.")
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
        self._notify_users(
            item,
            self._tenant_admin_ids(empresa_id),
            "traspaso_solicitado",
            "Nueva solicitud de traspaso",
            f"{user.name} solicita mover {item.cantidad} unidad(es) de {item.sucursal_origen.name} a {item.sucursal_destino.name}. Revisa y ajusta la cantidad antes de aprobar.",
        )
        return item

    def list(self, user: User, estado: str | None = None) -> list[TraspasoInventario]:
        query = self.db.query(TraspasoInventario)
        if not user.is_platform_admin:
            query = query.filter(TraspasoInventario.empresa_id == self._tenant_id(user))
        if self._is_branch_manager(user):
            employee = self.db.query(Empleado).filter(Empleado.user_id == user.id).first()
            assigned = {employee.sucursal_id} if employee and employee.sucursal_id else set()
            if employee:
                assigned.update(item.sucursal_id for item in (employee.asignaciones or []))
            query = query.filter(or_(
                TraspasoInventario.solicitado_por_id == user.id,
                TraspasoInventario.sucursal_destino_id.in_(assigned or {-1}),
            ))
        if estado:
            query = query.filter(TraspasoInventario.estado == estado)
        return query.order_by(TraspasoInventario.created_at.desc(), TraspasoInventario.id.desc()).all()

    def approve(self, traspaso_id: int, respuesta: str | None, user: User, cantidad: int | None = None) -> TraspasoInventario:
        self._assert_tenant_admin(user)
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
        approved_quantity = cantidad or item.cantidad
        if approved_quantity <= 0:
            raise BadRequestException("La cantidad aprobada debe ser mayor a cero.")
        if not source or source.cantidad < approved_quantity:
            raise ConflictException("El stock de origen ya no es suficiente para aprobar el traspaso.")

        source.cantidad -= approved_quantity
        if destination:
            destination.cantidad += approved_quantity
        else:
            destination = StockInventario(
                producto_color_id=item.producto_color_id,
                talla_id=item.talla_id,
                sucursal_id=item.sucursal_destino_id,
                cantidad=approved_quantity,
                precio_variante=source.precio_variante,
                medidas=dict(source.medidas or {}),
            )
            self.db.add(destination)

        item.estado = "aprobado"
        item.cantidad_aprobada = approved_quantity
        item.respuesta = respuesta
        item.procesado_por_id = user.id
        item.procesado_en = datetime.now(timezone.utc)
        self._audit(user, f"Aprobó traspaso de inventario #{item.id}; movió {approved_quantity} unidades")
        self.db.commit()
        self.db.refresh(item)
        self._notify_users(
            item,
            {item.solicitado_por_id},
            "traspaso_aprobado",
            "Traspaso aprobado",
            f"El administrador aprobó {approved_quantity} unidad(es) de {item.sucursal_origen.name} a {item.sucursal_destino.name}.",
        )
        return item

    def decide_without_movement(
        self, traspaso_id: int, estado: str, respuesta: str | None, user: User
    ) -> TraspasoInventario:
        if estado == "rechazado":
            self._assert_tenant_admin(user)
        item = self._get_scoped(traspaso_id, user, lock=True)
        if estado == "cancelado" and item.solicitado_por_id != user.id and not self._is_tenant_admin(user):
            raise ForbiddenException("Solo quien creó la solicitud o el administrador del tenant puede cancelarla.")
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
        self._notify_users(
            item,
            {item.solicitado_por_id},
            f"traspaso_{estado}",
            "Traspaso rechazado" if estado == "rechazado" else "Solicitud de traspaso cancelada",
            respuesta or ("El administrador rechazó la solicitud de traspaso." if estado == "rechazado" else "La solicitud fue cancelada."),
        )
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
            "cantidad_aprobada": item.cantidad_aprobada,
            "cantidad_efectiva": item.cantidad_aprobada or item.cantidad,
            "estado": item.estado,
            "idempotency_key": item.idempotency_key,
            "observacion": item.observacion,
            "respuesta": item.respuesta,
            "solicitado_por": item.solicitado_por.name,
            "procesado_por": item.procesado_por.name if item.procesado_por else None,
            "created_at": item.created_at,
            "procesado_en": item.procesado_en,
        }
