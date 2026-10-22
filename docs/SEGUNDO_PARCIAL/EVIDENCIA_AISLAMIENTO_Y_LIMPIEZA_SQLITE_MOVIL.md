# Evidencia de Aislamiento y Limpieza Segura de Almacenamiento Local en Móvil SQLite (REQ-072)

## 1. Alcance y Requisitos Verificados
- **REQ-072**: Estrategia de aislamiento y limpieza segura de almacenamiento local en móvil SQLite por empresa+usuario.
- **Aislamiento Multi-tenant por Ámbito**: Cada tabla (`catalog_snapshots`, `authorized_branches`, `local_clients`, `local_sales`, `local_sale_details`, `local_reservations`, `local_reservation_details`, `sync_queue`) aísla sus registros mediante la columna `scope` (`empresa-{id}:usuario-{id}`). Las consultas de un usuario o empresa jamás retornan datos de otro ámbito.
- **Limpieza Segura y Protección de Transacciones**: Se implementó una política estricta de protección de transacciones fuera de línea (`pendiente`, `sincronizando`) frente a purgas accidentales, junto con métodos de desalojo de caché expirada y eliminación de registros resueltos.

## 2. Métodos y Capacidades Implementadas en Móvil (`LocalDatabaseService`)

1. **Gestión de Clientes Locales Aislados**:
   - `saveLocalClient(scope, client)`: Persiste clientes del tenant para ventas offline.
   - `loadLocalClients(scope)`: Recupera clientes respetando estrictamente el ámbito.
2. **Limpieza Segura de Caché (`clearScopeCache`)**:
   - Borra únicamente snapshots de catálogo, sucursales cacheadas y clientes locales del ámbito.
   - Preserva al 100% la cola de operaciones pendientes e historial transaccional.
3. **Purga Segura de Operaciones Resueltas (`purgeResolvedOperations`)**:
   - Elimina operaciones en estado `confirmada`, `rechazada` o `conflicto` junto con sus detalles en cascada.
   - Protege de forma inmutable las operaciones en estado `pendiente` y `sincronizando`.
4. **Desalojo por Antigüedad (`purgeExpiredCache`)**:
   - Elimina snapshots anteriores a un umbral TTL (por defecto 7 días).
5. **Diagnóstico Estructurado (`getStorageDiagnostics`)**:
   - Reporta conteo exacto de snapshots, sucursales, clientes locales y desglose de operaciones (`pending`, `syncing`, `confirmed`, `conflict`, `total`).
6. **Borrado Seguro del Ámbito (`safeWipeScope`)**:
   - Verifica existencia de transacciones pendientes y arroja `StateError` para prevenir pérdida de datos salvo que se invoque explícitamente `forceEvenIfPending: true`.
7. **Interfaz de Usuario Móvil (`OfflineOperationsScreen`)**:
   - Diálogo de diagnósticos de almacenamiento SQLite accesible desde la barra superior.
   - Opciones para purgar transacciones resueltas y limpiar caché local con retroalimentación vía SnackBar.

## 3. Pruebas Automatizadas y Verificación
- Archivo: `mobile/test/local_database_service_test.dart`
  - `persiste una reserva y su cola después de reabrir SQLite`: APROBADO
  - `una venta conserva detalle e importe y respeta el ámbito`: APROBADO
  - `aislamiento y persistencia de clientes locales por ámbito`: APROBADO
  - `clearScopeCache elimina snapshots y clientes pero preserva la cola de transacciones`: APROBADO
  - `purgeResolvedOperations elimina operaciones resueltas pero protege las pendientes`: APROBADO
  - `diagnósticos y safeWipeScope protegen transacciones pendientes de borrado accidental`: APROBADO
  - `StyleStoreApp smoke test`: APROBADO
- Total pruebas ejecutadas: 9 pruebas aprobadas (100% pasando).
- Análisis estático: `flutter analyze --no-pub` completado con 0 errores y 0 advertencias.
