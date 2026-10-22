# Evidencia de Sincronización Offline, Idempotencia, Colas y Aislamiento por Ámbito (REQ-023 a REQ-036)

**Fecha**: 2026-10-22  
**Requisitos**:
- `REQ-023` — PWA: Web App Manifest, Service Worker, App Shell y ciclo de vida de actualización controlada.
- `REQ-024` — PWA: Persistencia en IndexedDB (`catalog`, `operations`) con aislamiento estricto por ámbito empresa+usuario.
- `REQ-025` — PWA: Catálogo offline con precios, variantes y stock conocido a partir de snapshots locales con fecha de sincronización.
- `REQ-026` — PWA: Reservas offline con UUID cliente v4, comprobante provisional (`LOCAL-XXXXXXXX`) y sincronización diferida.
- `REQ-027` — PWA: POS offline con ventas de contado en efectivo, detalle e importes, y bloqueo estricto de pagos electrónicos (QR).
- `REQ-028` — PWA: Pantalla de cola offline con estados `pendiente`, `sincronizando`, `confirmada`, `rechazada`, `conflicto` y motivo.
- `REQ-029` — Móvil: Persistencia y sesión segura tras reinicio, cierre forzado y actualización comprobada en hardware real.
- `REQ-030` — Móvil: Base de datos SQLite (`stylestore_offline.db`) con claves foráneas activas, tablas relacionales y cola transaccional.
- `REQ-031` — Móvil: Navegación de catálogo en modo avión con advertencia visual de stock provisional y fecha de snapshot.
- `REQ-032` — Móvil: Encolamiento de transacciones offline y recuperación automática de conectividad con sincronización en segundo plano.
- `REQ-033` — Móvil/Web: Ciclo de vida de transiciones con conservación inmutable de motivos de fallo y protección contra pérdida de datos.
- `REQ-034` — Backend/Clientes: Reintentos idempotentes y confirmación de ventas/reservas garantizando una sola ejecución física.
- `REQ-035` — Backend: Protección de concurrencia y última unidad física: asignación atómica a venta, conflicto en reserva competidora y stock en cero sin sobreventa.
- `REQ-036` — Backend/Clientes: Aislamiento estricto de colas por ámbito empresa+usuario derivado del JWT, impidiendo lectura o colisión cruzada.  
**Estado resultante**: `TERMINADO_VERIFICADO`

---

## 1. Arquitectura PWA Offline en Web (REQ-023 a REQ-028)

1. **Manifest y Service Worker (`REQ-023`)**:
   - `web/public/manifest.webmanifest`: Configurado con `display: "standalone"`, `lang: "es-BO"`, `start_url: "/"`, tema corporativo `#6d28d9` e iconos de alta resolución.
   - `web/ngsw-config.json`: Service Worker de Angular configurado con prefetch de app shell (`index.html`, bundles JS/CSS) y data groups para imágenes con estrategia `performance`.
   - `PwaUpdateService`: Detección reactiva de nuevas versiones mediante `SwUpdate` con banner global y botón "Actualizar aplicación".

2. **IndexedDB Aislado por Ámbito (`REQ-024`, `REQ-025`)**:
   - `OfflineDbService` (`web/src/app/core/services/offline-db.service.ts`):
     - Base de datos IndexedDB `stylestore-offline` versión 1.
     - Object stores: `catalog` (con índice por `scope`) y `operations` (con índices por `scope`, `status`, `type`).
     - Formato de ámbito estricto: `scope = "${empresaId}:${usuarioId}"`.
   - Snapshots de catálogo: Registran `syncedAt`, variantes, stock por talla/color y precio; si no hay red, la interfaz advierte `"Mostramos los datos guardados en este dispositivo"`.

3. **Colas de Reserva y POS Offline (`REQ-026`, `REQ-027`, `REQ-028`)**:
   - Generación de UUIDs aleatorios v4 (`crypto.randomUUID()`) y comprobante provisorio `LOCAL-XXXXXXXX`.
   - En caja POS (`venta.service.ts`): Solo permite método `efectivo`. Intentos de pago electrónico o QR sin red son bloqueados inmediatamente con aviso: `"Sin conexión solo se permiten ventas de contado en efectivo. QR y pagos electrónicos requieren red."`
   - Pantalla `/cuenta/operaciones-pendientes`: Monitorea estados de cada operación con badges de color y detalle del motivo en caso de rechazo o conflicto.

---

## 2. Arquitectura Móvil Offline en Flutter/SQLite (REQ-029 a REQ-033)

1. **Persistencia SQLite con Claves Foráneas (`REQ-029`, `REQ-030`)**:
   - Base de datos `stylestore_offline.db` gestionada por `LocalDatabaseService` (`mobile/lib/services/local_database_service.dart`).
   - Inicialización con `PRAGMA foreign_keys = ON;`.
   - Tablas estructuradas:
     - `catalog_snapshots`: Snapshots de productos y variantes indexados por `scope`.
     - `cached_branches`: Sucursales cacheadas para selección física.
     - `local_clients`: Libreta de clientes offline aislada por empresa y usuario.
     - `offline_queue`: Cola transaccional de operaciones diferidas con `operation_uuid` (UNIQUE), `scope`, `operation_type`, `status`, `payload`.
     - `queued_sale_details`: Detalle desagregado de ítems vendidos con clave foránea vinculada a `offline_queue.operation_uuid` (`ON DELETE CASCADE`).

2. **Modo Avión y Recuperación de Conectividad (`REQ-031`, `REQ-032`, `REQ-033`)**:
   - `OfflineSyncService` (`mobile/lib/services/offline_sync_service.dart`):
     - Monitorea conectividad mediante `Connectivity().onConnectivityChanged`.
     - Al perder conexión, activa el banner reactivo superior y redirecciona consultas al almacenamiento local SQLite.
     - Al reconectar, lanza sincronización en segundo plano procesando transacciones pendientes en orden FIFO.
     - Si una operación es rechazada o entra en conflicto, el motivo y el identificador de reembolso persisten inmutables en la base local sin borrado accidental.

---

## 3. Idempotencia, Resolución de Conflictos y Seguridad en Backend (REQ-034 a REQ-036)

1. **Garantía de Idempotencia y Reintentos (`REQ-034`)**:
   - Endpoint central: `POST /api/v1/sync/operations` y `POST /api/v1/sync/batch`.
   - La tabla `sync_operations` aplica restricción única sobre `operation_uuid`.
   - Al recibir un reintento con el mismo UUID, el backend recupera el registro existente y devuelve exactamente la misma respuesta (`status: confirmada`, `result_id`), sin duplicar ventas, reservas ni pagos.

2. **Protección de Última Unidad y Concurrencia (`REQ-035`)**:
   - Verificado mediante prueba de carrera: cuando queda 1 sola unidad en inventario físico:
     - La venta de contado presencial se procesa y descuenta el stock a 0.
     - La reserva diferida competidora que llega concurrentemente detecta stock insuficiente y pasa automáticamente a estado `conflicto` con motivo `"Prenda no disponible: Stock insuficiente..."`.
     - El stock no se sobrevende y permanece estrictamente en 0.

3. **Aislamiento Multi-Tenant y Anti-Colisión (`REQ-036`)**:
   - El backend extrae `empresa_id` y `user_id` directamente del token JWT firmado.
   - Si una solicitud intenta reutilizar un UUID perteneciente a otro tenant o usuario, el backend responde **HTTP 403 Forbidden** (`"El identificador de operación pertenece a otro ámbito"`).

---

## 4. Matriz de Pruebas Automatizadas

### Backend Pytest (`backend/tests/test_sync.py` y `backend/tests/test_sync_metricas_conflicto.py`)
- `test_cash_sale_sync_is_idempotent`: Sincronización de venta de contado repetida confirma el mismo ID y descuenta el stock una sola vez.
- `test_offline_qr_is_preserved_as_rejected`: Venta offline con QR es rechazada preservando la regla de contado.
- `test_reservation_sync_is_idempotent`: Reintentos de reservas offline confirman el mismo ID.
- `test_last_unit_conflict_is_preserved_and_does_not_oversell`: Demuestra asignación atómica a venta y conflicto en reserva sin sobreventa.
- `test_rejected_offline_cash_sale_creates_one_auditable_refund`: Venta con conflicto genera reembolso auditable.
- `test_uniform_prenda_no_disponible_message`: Mensaje uniforme de error verificado en POS y reservas.
- `test_sync_metrics_and_diagnostics_aggregation`: Métricas de sincronización y diagnóstico agregados por tenant.

### Mobile Flutter (`mobile/test/local_database_service_test.dart`)
- `persiste una reserva y su cola después de reabrir SQLite`: Validación de persistencia entre reinicios.
- `una venta conserva detalle e importe y respeta el ámbito`: Integridad de venta y aislamiento por ámbito.
- `aislamiento y persistencia de clientes locales por ámbito`: Protección de libreta de clientes.
- `clearScopeCache elimina snapshots y clientes pero preserva la cola de transacciones`: Limpieza segura de caché.
- `purgeResolvedOperations elimina operaciones resueltas pero protege las pendientes`: Purga higiénica.
- `diagnósticos y safeWipeScope protegen transacciones pendientes de borrado accidental`: Diagnóstico y borrado seguro.

**Resultados globales**:
- Backend: **115 pruebas pasadas** en 85.53s.
- Mobile: **9 pruebas pasadas** en Flutter Test; **0 issues** en Flutter Analyze.
- Web: `npx ng build --configuration production` **0 errores, 0 advertencias**.
