"""Conciliación idempotente de PayPal, inventario y reembolsos automáticos."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.models.cliente import Cliente
from app.models.notificacion import Notificacion
from app.models.orden_venta import OrdenVenta
from app.models.pago import Pago
from app.models.stock_inventario import StockInventario
from app.models.user import User
from app.services.notificacion_service import NotificacionService
from app.services.pago_service import PagoService
from app.services.paypal_service import paypal_service


class PaymentReconciliationService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def capture_id(payload: dict, fallback: str | None = None) -> str | None:
        for unit in payload.get("purchase_units", []) or []:
            for capture in (unit.get("payments", {}) or {}).get("captures", []) or []:
                if capture.get("id"):
                    return str(capture["id"])
        return fallback

    async def reconcile(self, payment: Pago) -> tuple[Pago, str]:
        """Consulta/captura PayPal y deja un único resultado durable en la BD."""
        payment = (
            self.db.query(Pago)
            .filter(Pago.id == payment.id)
            .with_for_update(of=Pago)
            .one()
        )
        payment.operation_uuid = payment.operation_uuid or str(uuid4())
        order = payment.orden_venta

        if payment.estado == "aprobado" and order.estado == "pagada":
            self.db.commit()
            return payment, "El pago ya estaba confirmado."
        if payment.estado == "reembolsado":
            self.db.commit()
            return payment, "El pago fue reembolsado por conflicto de stock."
        if not payment.paypal_order_id:
            self.db.commit()
            return payment, "El pago todavía no tiene una orden PayPal asociada."

        remote = await paypal_service.get_order(
            payment.paypal_order_id, allow_mock=settings.ALLOW_MOCK_PAYPAL
        )
        remote_status = str(remote.get("status") or "").upper()
        if remote_status == "APPROVED":
            remote = await paypal_service.capture_order(
                payment.paypal_order_id, allow_mock=settings.ALLOW_MOCK_PAYPAL
            )
            remote_status = str(remote.get("status") or "").upper()
        if remote_status not in {"COMPLETED", "SAVED"}:
            self.db.commit()
            return payment, "PayPal aún no registra una aprobación completada."

        capture_id = self.capture_id(remote, payment.paypal_capture_id)
        if not capture_id:
            self.db.commit()
            return payment, "PayPal confirmó el cobro, pero aún no entregó su identificador de captura."
        payment.paypal_capture_id = capture_id

        conflict = self._apply_inventory(order)
        if conflict:
            return await self._refund_stock_conflict(payment, order, conflict)

        payment.estado = "aprobado"
        payment.metodo_pago = "paypal"
        order.estado = "pagada"
        order.metodo_pago = "paypal"
        self.db.commit()
        self.db.refresh(payment)
        PagoService(self.db).confirmar(payment)
        NotificacionService(self.db).notificar_experiencia_poscompra(order)
        return payment, "Pago confirmado y stock consolidado correctamente."

    def _apply_inventory(self, order: OrdenVenta) -> str | None:
        if order.inventario_descontado:
            return None
        locked: list[tuple[StockInventario, int, str]] = []
        for detail in order.detalles:
            if detail.stock_inventario_id is None:
                return f"La variante de {detail.producto_nombre} ya no existe."
            stock = (
                self.db.query(StockInventario)
                .filter(StockInventario.id == detail.stock_inventario_id)
                .with_for_update(of=StockInventario)
                .first()
            )
            if not stock or stock.cantidad < detail.cantidad:
                available = stock.cantidad if stock else 0
                return (
                    f"{detail.producto_nombre} ({detail.talla_nombre or 'sin talla'}, "
                    f"{detail.color_nombre or 'sin color'}) requiere {detail.cantidad} y quedan {available}."
                )
            locked.append((stock, detail.cantidad, detail.producto_nombre))
        for stock, quantity, _ in locked:
            stock.cantidad -= quantity
        order.inventario_descontado = True
        return None

    async def _refund_stock_conflict(
        self, payment: Pago, order: OrdenVenta, conflict: str
    ) -> tuple[Pago, str]:
        payment.estado = "reembolso_pendiente"
        payment.refund_reason = f"Conflicto de stock al conciliar: {conflict}"
        order.estado = "conflicto_stock"
        self.db.commit()

        result = await paypal_service.refund_capture(
            payment.paypal_capture_id or "",
            idempotency_key=payment.operation_uuid or str(payment.id),
            allow_mock=settings.ALLOW_MOCK_PAYPAL,
        )
        refund_status = str(result.get("status") or "").upper()
        if refund_status not in {"COMPLETED", "PENDING"}:
            return payment, "El conflicto fue detectado; PayPal todavía no confirmó el reembolso automático."
        if refund_status == "PENDING":
            payment.paypal_refund_id = str(result.get("id") or "") or None
            self.db.commit()
            return payment, "PayPal recibió el reembolso y todavía lo está procesando."

        payment.paypal_refund_id = str(result.get("id") or "") or None
        payment.estado = "reembolsado"
        payment.refunded_at = datetime.now(timezone.utc)
        order.estado = "reembolsada_stock"
        self.db.commit()
        self.db.refresh(payment)
        self._notify_refund(order, payment, conflict)
        return payment, "Prenda agotada; el cobro fue reembolsado automáticamente."

    def _notify_refund(self, order: OrdenVenta, payment: Pago, conflict: str) -> None:
        cliente = self.db.query(Cliente).filter(Cliente.codigo == order.codigo_cliente).first()
        if not cliente or not cliente.user_id:
            return
        action_url = f"/cuenta/mis-compras?orden_id={order.id}"
        existing = self.db.query(Notificacion).filter(
            Notificacion.user_id == cliente.user_id,
            Notificacion.tipo == "reembolso_stock_paypal",
            Notificacion.url_accion == action_url,
        ).first()
        if existing:
            return
        NotificacionService(self.db).crear_notificacion(
            user_id=cliente.user_id,
            empresa_id=payment.empresa_id,
            tipo="reembolso_stock_paypal",
            titulo="Prenda agotada · dinero devuelto",
            mensaje=(
                "Lo sentimos, otra compra agotó la prenda antes de sincronizar tu operación. "
                f"PayPal devolvió Bs. {float(payment.monto):.2f} a la cuenta de origen. "
                f"Referencia: {payment.operation_uuid}. Detalle: {conflict}"
            ),
            url_accion=action_url,
            enviar_email=True,
            enviar_push=True,
        )
