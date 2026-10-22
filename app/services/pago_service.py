"""Finalizacion auditable e idempotente de pagos aprobados."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.core.email import send_notification_email
from app.models.notificacion import Notificacion
from app.models.pago import Pago


class PagoService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _recibo_numero(pago_id: int) -> str:
        return f"REC-{pago_id:08d}"

    def confirmar(self, pago: Pago) -> Pago:
        """Asocia tenant y emite una sola constancia/notificacion por pago aprobado."""
        if pago.id is None:
            self.db.flush()
        pago = (
            self.db.query(Pago)
            .filter(Pago.id == pago.id)
            .with_for_update(of=Pago)
            .one()
        )

        orden = pago.orden_venta
        if pago.empresa_id is None and orden and orden.sucursal:
            pago.empresa_id = orden.sucursal.empresa_id

        if pago.estado != "aprobado":
            self.db.commit()
            self.db.refresh(pago)
            return pago

        if not pago.recibo_numero:
            pago.recibo_numero = self._recibo_numero(pago.id)

        user = orden.cliente.user if orden and orden.cliente else None
        notificacion = None
        if user:
            notificacion = (
                self.db.query(Notificacion)
                .filter(Notificacion.pago_id == pago.id)
                .first()
            )
            if not notificacion:
                notificacion = Notificacion(
                    user_id=user.id,
                    pago_id=pago.id,
                    tipo="pago_confirmado",
                    titulo="Pago confirmado",
                    mensaje=(
                        f"Confirmamos tu pago de Bs. {pago.monto} para la orden "
                        f"#{pago.orden_venta_id}. Recibo {pago.recibo_numero}."
                    ),
                    url_accion=f"/cuenta/mis-pagos?recibo={pago.id}",
                    leida=False,
                )
                self.db.add(notificacion)

        if user and user.email and pago.email_confirmacion_enviado_at is None:
            pago.email_confirmacion_intentos += 1
            action_url = f"{settings.FRONTEND_URL.rstrip('/')}/cuenta/mis-pagos?recibo={pago.id}"
            enviado = send_notification_email(
                to_email=user.email,
                subject=f"Pago confirmado - {pago.recibo_numero}",
                title="Tu pago fue confirmado",
                message=(
                    f"Recibimos Bs. {pago.monto} para la orden #{pago.orden_venta_id}. "
                    f"Tu comprobante es {pago.recibo_numero}."
                ),
                action_url=action_url,
                action_text="Ver recibo",
            )
            if enviado:
                pago.email_confirmacion_enviado_at = datetime.now(timezone.utc)

        # El bloqueo de fila conserva recibo, notificacion y marca de correo
        # como una sola finalizacion; una repeticion posterior los reutiliza.
        self.db.commit()
        self.db.refresh(pago)

        return pago
