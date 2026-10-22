# Evidencia REQ-056/057 — confirmación y recibo de pago

Fecha: 2026-10-21

## Cobertura implementada

- Cada pago nuevo guarda `empresa_id` obligatorio y el historial del cliente se filtra por su tenant activo.
- Al aprobarse un pago se asigna una constancia estable `REC-########`.
- Una restricción única sobre `notificaciones.pago_id` impide duplicar el evento `pago_confirmado`.
- El cierre usa bloqueo de fila y `email_confirmacion_enviado_at`; un replay reutiliza el recibo/notificación y no reenvía un correo ya confirmado.
- PayPal, caja/QR, confirmación online, venta presencial y diferencia de un cambio usan el mismo servicio.
- Web abre el recibo desde la URL de la notificación y usa moneda boliviana. Mobile expone recibo y estado dentro de Mis Pedidos.

## Verificación local

- `pytest -q`: 84 pruebas aprobadas.
- `test_payment_confirmation_is_tenant_scoped_and_idempotent`: dos ejecuciones producen un recibo, una notificación y un envío.
- Migración `0b2c4d6e8f90`: `upgrade`, `downgrade` y nuevo `upgrade` aprobados en PostgreSQL desde `fa91b3d5e678`.
- Angular producción: bundle `main-EL2XGJWT.js`.
- Flutter: `flutter analyze` sin problemas y 5 pruebas aprobadas.

## Pendiente para TERMINADO_VERIFICADO

- Aplicar `alembic upgrade head` en Railway y comprobar un pago real/sandbox con SMTP configurado.
- Guardar captura del recibo Web/Mobile y del correo recibido en el paquete final de evidencias.
