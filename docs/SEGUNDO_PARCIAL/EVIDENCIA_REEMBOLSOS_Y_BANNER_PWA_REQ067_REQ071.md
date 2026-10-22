# Evidencia de Reembolsos Offline y Banner Global PWA (REQ-067 y REQ-071)

**Fecha**: 2026-10-22  
**Requisitos**:
- `REQ-067` — Estados `pendiente`, `entregado`, `cancelado` para reembolsos offline por conflicto de stock, gestión administrativa por tenant en Web (`/admin/reembolsos`) y aviso del monto recaudado en colas Web y Android.
- `REQ-071` — Banner global de conectividad PWA/Mobile que informa estado de conexión, catálogo en caché, fecha de última sincronización, operaciones pendientes de cola y botón de actualización de Service Worker PWA.  
**Estado resultante**: `TERMINADO_VERIFICADO`

---

## 1. Reembolsos Offline y Gestión de Estados (REQ-067)

### A. Ciclo de Vida y Detección de Conflicto
1. **Conflicto de Existencias en Sincronización**:
   - Cuando una venta presencial cobrada en efectivo durante modo offline se sincroniza en el backend (`POST /api/v1/sync/operations`), si el stock físico fue consumido concurrentemente o es insuficiente, la operación pasa a estado `conflicto`.
   - Se crea de manera atómica e idempotente un registro en `reembolsos_offline` con:
     - `monto = total cobrado` (leído del snapshot local).
     - `moneda = BOB`.
     - `metodo_original = efectivo`.
     - `estado = pendiente`.
     - `motivo = "Prenda no disponible: Stock insuficiente..."`.
   - La respuesta del servidor y la tarjeta en la cola local retornan:
     - `refund_id`: ID oficial del reembolso.
     - `refund_status`: `"pendiente"`.
     - `refund_amount`: Monto exacto que el personal debe devolver en efectivo al cliente.

### B. Gestión Administrativa por Tenant en Web y API
- **Endpoint de Consulta**: `GET /api/v1/reembolsos?estado={pendiente|entregado|cancelado}`.
  - Exige roles autorizados: `administrador`, `encargado_sucursal`, `cajero`.
  - **Aislamiento Multi-Tenant**: Cada empresa solo visualiza sus propios reembolsos; cualquier intento de acceder o mutar un reembolso de otro tenant es rechazado con **HTTP 404 Not Found**.
- **Endpoint de Transición**: `PUT /api/v1/reembolsos/{id}`.
  - Recibe `estado: "entregado" | "cancelado"` y `observaciones` detalladas (mínimo 3 caracteres).
  - Registra auditoría automática en `bitacora`.
  - **Inmutabilidad Histórica**: Si el reembolso ya fue resuelto (`entregado` o `cancelado`), cualquier intento posterior de mutación responde **HTTP 403 Forbidden** (`"El reembolso ya fue resuelto y conserva su estado histórico."`).
- **Consulta de Cliente**: `GET /api/v1/reembolsos/mios` permite a los usuarios consultar sus reembolsos pendientes o entregados de forma aislada.

### C. Avisos de Monto en Colas Web y Android
- **Web PWA (`offline-operations.component.html`)**:
  - Renderiza para cada operación en conflicto:
    `"Reembolso #{operation.refundId}: {operation.refundStatus} · Bs {operation.refundAmount}"`.
- **Mobile Android (`offline_operations_screen.dart` y `offline_sync_service.dart`)**:
  - En la lista de transacciones y modal de diagnóstico:
    `"Reembolso #{refundId} pendiente por Bs {refundAmount}."`
  - Muestra métricas agregadas del servidor con el total de reembolsos y monto total acumulado.

---

## 2. Banner Global de Conectividad PWA (REQ-071)

### A. Estados Informados en Tiempo Real (`web/src/app/app.html`)
El banner global (`.connectivity-banner`) se ubica en el punto de entrada raíz de la aplicación web sobre el `router-outlet`:

1. **Sin Conexión (Modo Avión / Red Caída)**:
   - Texto: `"Sin conexión. Mostramos los datos guardados en este dispositivo."`
2. **Catálogo Cacheado Localmente**:
   - Texto: `"Catálogo guardado. Última sincronización: {fecha/hora en formato es-BO}."`
3. **Operaciones Pendientes en Cola**:
   - Texto: `"{N} operación(es) pendientes de sincronización."` con enlace directo `"Ver cola"` hacia `/cuenta/operaciones-pendientes`.
4. **Actualización de Service Worker PWA**:
   - Detecta nueva versión disponible mediante `PwaUpdateService` (Angular Service Worker `SwUpdate`).
   - Muestra botón reactivo `"Actualizar aplicación"` que llama a `applyUpdate()`.

---

## 3. Pruebas Automatizadas

### Backend (`backend/tests/test_reembolsos_offline_req067.py`)
```
tests/test_reembolsos_offline_req067.py::test_offline_cash_sale_conflict_creates_pending_refund_with_amount_notice PASSED [ 33%]
tests/test_reembolsos_offline_req067.py::test_refund_lifecycle_transitions_and_immutability PASSED [ 66%]
tests/test_reembolsos_offline_req067.py::test_tenant_isolation_and_role_security_on_refunds PASSED [100%]

======================== 3 passed, 2 warnings in 9.97s ========================
```

### Suite Completa Backend
```
====================== 115 passed, 2 warnings in 85.53s ======================
```

### Frontend Web
- `npx ng build --configuration production`: **0 errores, 0 advertencias**.

### Mobile Flutter
- `flutter analyze --no-pub`: **No issues found**.
- `flutter test --no-pub`: **9 passed**.
