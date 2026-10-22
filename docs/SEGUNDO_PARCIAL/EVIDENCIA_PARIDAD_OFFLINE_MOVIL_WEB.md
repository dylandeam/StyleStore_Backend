# Evidencia de Paridad Móvil y Web en Operaciones Offline y Métricas de Sincronización (REQ-069)

## 1. Alcance y Requisitos Verificados
- **REQ-069**: Paridad móvil/web en operaciones offline compartidas (contratos, colas transaccionales, visualización reactiva de conectividad, integración con métricas centralizadas de sincronización y mitigación de conflictos).
- **Consistencia de Contratos Compartidos**:
  - Tanto Web (IndexedDB vía `OfflineDbService` y `OfflineOperationsService`) como Móvil (SQLite vía `LocalDatabaseService` y `OfflineSyncService`) implementan la estructura simétrica de operaciones diferidas (`operacion_uuid`, `scope`, `reserva`, `venta_efectivo`, `payload_version`, `status`, `reason`).
  - Ambas plataformas reportan comprobantes unificados (`LOCAL-XXXXXXXX`).

## 2. Implementaciones para Paridad Total Móvil-Web

1. **Monitoreo Reactivo de Conectividad (`OfflineSyncService`)**:
   - `isOnline`: Detección en tiempo real del estado de red mediante `Connectivity().onConnectivityChanged`.
   - Disparo automático de sincronización idempotente en segundo plano tan pronto se restablece la conexión.
2. **Banner Global de Conectividad Móvil (`OfflineConnectivityBanner`)**:
   - Paridad directa con `<aside class="connectivity-banner">` de Angular PWA (`web/src/app/app.html`).
   - Muestra aviso visual destacado cuando no hay conexión a internet informando el uso de la base de datos local SQLite.
   - Si existen transacciones encoladas, muestra la cantidad exacta de operaciones pendientes con acceso directo a la pantalla de cola (`AppRoutes.offlineOperations`).
3. **Métricas Remotas Centralizadas (`GET /api/v1/sync/metricas`)**:
   - Móvil ahora consume el endpoint oficial de diagnóstico del backend implementado para `REQ-070` (`ApiConfig.syncMetricasUrl`).
   - El diálogo de diagnósticos en `OfflineOperationsScreen` presenta tanto el estado del SQLite local (snapshots, sucursales, clientes locales, cola) como el resumen centralizado del tenant (operaciones procesadas, confirmadas, conflictos, tasa de éxito % y reembolsos vinculados).

## 3. Pruebas y Verificaciones
- **Backend**: 101 pruebas aprobadas en Pytest (100% pasando, 0 regresiones).
- **Mobile**:
  - `flutter test --no-pub`: 9 pruebas aprobadas (100% pasando).
  - `flutter analyze --no-pub`: 0 errores, 0 advertencias.
- **Web**: `npm run build` completado exitosamente sin errores de compilación ni empaquetado.
