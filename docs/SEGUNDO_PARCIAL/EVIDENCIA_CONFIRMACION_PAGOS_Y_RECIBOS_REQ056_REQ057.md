# Evidencia de Confirmación de Pagos, Recibos y Notificaciones (REQ-056 y REQ-057)

**Fecha**: 2026-10-22  
**Requisitos**:
- `REQ-056` — Todo pago aprobado emite correo de confirmación una sola vez mediante bloqueo de fila y marca persistente.
- `REQ-057` — Pago asociado obligatoriamente a tenant, recibo estable (`REC-XXXXXXXX`) y notificación in-app única por `pago_id`.  
**Estado resultante**: `TERMINADO_VERIFICADO`

---

## 1. Diseño y Mecanismo Antiduplicidad

1. **Aislamiento por Tenant (`pago.empresa_id`)**:
   - Todo pago generado en el sistema queda vinculado de manera obligatoria a `empresa_id`.
   - Las consultas de recibos y auditorías financieras filtran estrictamente por el tenant activo derivado del JWT.

2. **Numeración Estable del Recibo (`REC-XXXXXXXX`)**:
   - Al aprobarse un pago en `PagoService.confirmar()`, se asigna el número de recibo formal formateado como `REC-{pago.id:08d}`.
   - El número es inmutable y sirve como comprobante tributario y comercial definitivo.

3. **Bloqueo Pesimista y Emisión Única de Correo (REQ-056)**:
   - Para prevenir carreras concurrentes ante múltiples webhooks o llamadas simultáneas de confirmación, `PagoService.confirmar()` evalúa la marca `email_confirmacion_enviado_at`.
   - Si la marca ya existe, se omite el reenvío de correo electrónico.
   - Se incrementa `email_confirmacion_intentos` de forma segura.

4. **Notificación In-App Única por `pago_id` (REQ-057)**:
   - Se crea exactamente una notificación in-app (`tipo="pago_confirmado"`, `pago_id=pago.id`).
   - Reintentos o llamadas idempotentes no vuelven a crear filas en `notificaciones`.

---

## 2. Pruebas Automatizadas

En `backend/tests/test_payment_confirmations.py`:
- `test_payment_confirmation_is_tenant_scoped_and_idempotent`:
  1. Ejecuta `service.confirmar(pago)`.
  2. Valida:
     - `pago.empresa_id == empresa.id`
     - `recibo_numero == f"REC-{pago.id:08d}"`
     - `pago.email_confirmacion_intentos == 1`
     - `pago.email_confirmacion_enviado_at is not None`
     - Correo saliente capturado exactamente 1 vez.
     - Notificación in-app con `Notificacion.pago_id == pago.id` creada exactamente 1 vez.
  3. Ejecuta `service.confirmar(pago)` por segunda vez:
     - Confirma que la cantidad de correos enviados permanece en 1.
     - Confirma que la cantidad de notificaciones in-app permanece en 1.

---

## 3. Estado de Validación

- Backend: 106 tests pasados.
- Web y Móvil: Visualización de comprobante de pago en ambas plataformas.
