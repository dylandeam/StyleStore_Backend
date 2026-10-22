# Evidencia del Ciclo de Vida de Suscripciones, Vencimiento y Renovación PayPal (REQ-021, REQ-022 y REQ-073)

**Fecha**: 2026-10-22  
**Requisitos**:
- `REQ-021` — Alta, cambio, renovación, estado, vigencia, snapshot y bloqueos operativos implementados; clientes no pueden cambiar el plan del tenant y el vencimiento bloquea capacidades.
- `REQ-022` — Renovación auditada desde consola maestra y administración de precios/planes sin overrides simulados inseguros.
- `REQ-073` — El vencimiento marca la contratación como vencida e inactiva el tenant; solo el administrador conserva la renovación y la reactivación exige captura PayPal `COMPLETED`. Web y Móvil abren checkout PayPal real.  
**Estado resultante**: `TERMINADO_VERIFICADO`

---

## 1. Reglas del Ciclo de Suscripciones

1. **Inmutabilidad y Snapshots**:
   - Cada contratación guarda `precio_snapshot` y `moneda_snapshot` al momento de la orden.
   - Modificaciones futuras en el catálogo maestro de planes no alteran los contratos en curso.

2. **Vencimiento e Inactivación Automática (REQ-021 / REQ-073)**:
   - Al expirar la fecha de vigencia (`contract.fecha_fin < hoy`), `PlanService.reconcile_tenant_access()` actualiza la contratación a estado `vencida` e inactiva la empresa (`empresa.active = False`, `inactive_reason = "subscription_expired"`).
   - Todos los endpoints operativos de la empresa (reportes, catálogo, sucursales, pedidos) responden HTTP 403 Forbidden indicando que el tenant está inactivo por suscripción vencida.

3. **Superficie Restringida de Renovación**:
   - Ningún rol de cliente o personal no autorizado puede modificar el plan de la empresa.
   - El administrador de la empresa conserva acceso exclusivo a la superficie de renovación:
     - `GET /api/v1/planes`: Consulta de planes y precios vigentes.
     - `POST /api/v1/planes/paypal/crear-orden`: Creación de la orden de pago en PayPal Orders v2.
     - `POST /api/v1/planes/paypal/capturar-orden`: Captura del pago y validación contra PayPal oficial.

4. **Eliminación de Activaciones Manuales Inseguras (REQ-022)**:
   - Se eliminó el formulario y endpoint que permitía activar manualmente contratos con `pago_confirmado: true`.
   - `PUT /api/v1/empresas/{id}/suscripcion` responde HTTP 403 Forbidden para forzar el flujo formal de pago.
   - La reactivación del tenant requiere obligatoriamente una captura con estado `COMPLETED`, coincidencia de importe/moneda y asignación de referencia `CAP-PAYPAL-XXXXXXXX`.

---

## 2. Consumo en Web y Mobile

- **Web (`web/src/app/features/planes/`)**:
  - `planes.component.ts`: Los administradores tenant visualizan tarjetas de planes, beneficios y botón de pago PayPal integrado vía PayPal Buttons SDK o redirección aprobada.
  - El administrador SaaS supervisa precios y configuraciones globales.
- **Mobile (`mobile/lib/screens/plans/`)**:
  - `plans_screen.dart`: Interfaz nativa para visualización de planes y apertura de flujo PayPal oficial mediante `url_launcher`. El botón de contratación está oculto para clientes y solo activo para el administrador tenant.

---

## 3. Pruebas Automatizadas

En `backend/tests/test_tenant_foundation.py`:
- `test_plan_minimums_and_operational_capabilities_are_enforced`:
  - Simula la expiración del contrato (`fecha_fin = ayer`).
  - Valida bloqueo con HTTP 403 en `/reportes/dashboard-stats`.
  - Confirma que el tenant queda en `inactive_reason = "subscription_expired"`.
  - Verifica rechazo de creación de contratación simulada con `pago_confirmado=False` (HTTP 400).
  - Ejecuta la creación y captura PayPal (`/planes/paypal/crear-orden` y `/planes/paypal/capturar-orden`).
  - Valida estado `pagado`, prefijo `CAP-PAYPAL-` y reactivación inmediata del tenant (`active = True`).
  - Comprueba que el acceso a los endpoints operativos queda restituido exitosamente.

---

## 4. Estado de Validación

- Backend: 106 tests pasados (100% de éxito).
- Web: Build limpio sin errores.
- Mobile: Flutter analyze 0 issues, tests 9 pasados.
