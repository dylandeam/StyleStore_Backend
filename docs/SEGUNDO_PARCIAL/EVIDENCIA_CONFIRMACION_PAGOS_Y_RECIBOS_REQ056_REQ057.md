# Evidencia de Confirmación de Pagos, Recibos y Notificaciones (REQ-056 y REQ-057)

**Fecha**: 2026-10-24
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

- Backend: 127 pruebas recolectadas y cubiertas; 125 aprobaron en la ejecución integral, el único caso
  bloqueado por permisos de la carpeta temporal global de Windows aprobó al repetirse con un directorio
  temporal local, y la nueva prueba de no filtración de tokens aprobó en la ejecución focalizada.
- Web y Móvil: Visualización de comprobante de pago en ambas plataformas.
- Producción: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` y `FROM_EMAIL` están configuradas
  como variables protegidas del servicio backend en Railway. El deployment
  `70b4996f-e3e7-4b08-8450-c6568bedd28f` terminó en `SUCCESS`.
- Entrega externa: Gmail recibió el correo transaccional de StyleStore y la plantilla real
  `StyleStore - Confirmación de cambio de contraseña`. La credencial SMTP no se almacenó en el
  repositorio, la documentación ni los logs de prueba.
- Presentación y seguridad: el commit `624f929` agrega remitente visible `StyleStore`, alternativas
  texto plano/HTML UTF-8, escape de contenido dinámico y evita registrar enlaces privados cuando SMTP
  falla. Railway desplegó exactamente ese commit en `e19a3e14-83cf-4836-9ff7-98cebcbd7e88`
  (`SUCCESS`), la API respondió HTTP 200 y el envío transaccional posterior devolvió éxito.
- Rotación cerrada el 24/10/2026: con confirmación humana se revocó exclusivamente la contraseña de
  aplicación antigua `StyleStore Railway SMTP`. Google muestra como única credencial vigente
  `StyleStore Railway SMTP 2`; después de la revocación, Railway mantuvo la API en HTTP 200 y el envío
  transaccional real devolvió `True`.
- Fallo seguro: si SMTP no está disponible en un entorno administrado, la compra conserva la marca
  de correo pendiente para reintento y la solicitud de contraseña elimina el token no entregado antes
  de responder HTTP 503; no se comunica un éxito falso al usuario.
