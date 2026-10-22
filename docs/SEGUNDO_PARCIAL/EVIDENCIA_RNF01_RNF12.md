# Evidencia de Requisitos No Funcionales (RNF01–RNF12) — StyleStore SaaS

Fecha de auditoría: 21/10/2026.  
Alcance: Cumplimiento transversal verificado sobre Backend (FastAPI), Frontend Web (Angular 21 PWA) y Mobile (Flutter).  
Requisito matriz: `REQ-047 [P1]` del Plan Maestro del Segundo Parcial.

---

## Matriz de Cumplimiento Transversal

| RNF | Dimensión | Criterio de Aceptación | Evidencia Técnica y Archivos | Estado |
|---|---|---|---|---|
| **RNF01** | Seguridad y Control de Acceso (RBAC + Tenant) | Autenticación JWT robusta (access token 30m, refresh 7d, blacklist), autorización por roles (`is_platform_admin`, `admin_tenant`, `encargado`, `cajero`, `cliente`), validación en backend del 100% de endpoints y rechazo 401/403/404 a accesos cruzados. | `backend/app/api/deps.py`<br>`backend/app/services/auth_service.py`<br>`backend/app/api/v1/auth.py`<br>Test: `tests/test_auth.py`, `tests/test_reportes_multiempresa_comparativa.py` | `TERMINADO_VERIFICADO` |
| **RNF02** | Aislamiento Lógico de Datos Multi-tenant | Particionamiento lógico en PostgreSQL mediante `empresa_id` foráneo e indexado en todas las entidades operativas primarias y secundarias (productos, stock, órdenes, clientes, empleados, sucursales, archivos, reservas, pruebas virtuales). Cero fuga inter-tenant. | `backend/app/models/`<br>`backend/alembic/versions/2d4e6f809123_*.py`<br>`backend/docs/SEGUNDO_PARCIAL/EVIDENCIA_AISLAMIENTO_RECURSOS_SECUNDARIOS.md` | `TERMINADO_VERIFICADO` |
| **RNF03** | Durabilidad y Persistencia Local Offline | Persistencia estructurada sin red: IndexedDB en Angular PWA y SQLite relacional en Flutter Mobile. Conservación de claves foráneas, catálogo con variantes y cola de operaciones pendientes que sobreviven a reinicio de app. | `web/src/app/core/services/indexed-db.service.ts`<br>`web/src/app/core/services/offline-sync.service.ts`<br>`mobile/lib/services/offline_storage_service.dart`<br>`mobile/lib/services/sqlite_service.dart` | `TERMINADO_VERIFICADO` |
| **RNF04** | Integridad Transaccional y Consistencia de Stock | Transacciones ACID con bloqueo a nivel de fila (`with_for_update`), verificación central autoritativa del servidor para evitar sobreventa o stock negativo, y reversión automática ante fallos. | `backend/app/services/checkout_service.py`<br>`backend/app/services/stock_service.py`<br>`backend/app/services/pago_service.py`<br>Test: `tests/test_conflictos_stock_sync.py` | `TERMINADO_VERIFICADO` |
| **RNF05** | Idempotencia y Deduplicación Operativa | Contrato de sincronización `/sync` con UUID v4 único por operación comercial, bloqueo por clave idempotente, prevención de doble cargo en PayPal y confirmación única de pagos sin duplicar notificaciones ni correos. | `backend/app/api/v1/sync.py`<br>`backend/app/services/sync_service.py`<br>`backend/app/services/pago_service.py`<br>Test: `tests/test_pago_confirmacion_idempotente.py` | `TERMINADO_VERIFICADO` |
| **RNF06** | Recuperación y Resolución de Conflictos (Refund) | Manejo formal de operaciones rechazadas por agotamiento de existencias durante sincronización diferida: registro de estado conflicto, generación de nota de crédito / orden de reembolso auditable y conservación de histórico. | `backend/app/services/sync_service.py`<br>`backend/app/services/cambio_service.py`<br>`backend/docs/SEGUNDO_PARCIAL/EVIDENCIA_REEMBOLSOS_OFFLINE.md` | `TERMINADO_VERIFICADO` |
| **RNF07** | Mantenibilidad y Evolución de Esquemas (Alembic) | Cadena de migraciones lineal, aditiva y retrocompatible (`2d4e6f809123`) capaz de ejecutarse desde un esquema PostgreSQL vacío con 52 tablas sin truncar ni romper datos de la empresa legado `stylestore`. | `backend/alembic/versions/`<br>`backend/app/init_db.py`<br>Verificación: `alembic upgrade head` | `TERMINADO_VERIFICADO` |
| **RNF08** | Interoperabilidad y Paridad Multiplataforma | Interoperabilidad garantizada entre Backend (FastAPI), Web (Angular 21 PWA) y Mobile (Flutter). Contratos JSON estables, fallback multi-host dinámico en móvil y cumplimiento de estándares REST. | `web/src/environments/environment.ts`<br>`mobile/lib/config/api_config.dart`<br>`mobile/lib/services/api_service.dart`<br>Build Web: `main-S46ZNSZX.js` | `TERMINADO_VERIFICADO` |
| **RNF09** | Rendimiento, Eficiencia y Escalabilidad | Consultas SQL con joins optimizados y filtrado por tenant/sucursal, cálculo de geodistancia Haversine, exportación streaming de Excel y PDF con ReportLab/OpenPyXL, y modelos ML en Python puro deterministas (< 50ms). | `backend/app/core/geo.py`<br>`backend/app/services/report_service.py`<br>`backend/app/services/ml_service.py` | `TERMINADO_VERIFICADO` |
| **RNF10** | Observabilidad, Trazabilidad y Auditoría | Bitácora inmutable global de operaciones administrativas y comerciales críticas con usuario, empresa, acción, módulo, IP y timestamp. Trazabilidad completa de envíos (`TRK-XXXX`) y recibos de pago. | `backend/app/models/bitacora.py`<br>`backend/app/services/bitacora_service.py`<br>`backend/app/api/v1/bitacora.py` | `TERMINADO_VERIFICADO` |
| **RNF11** | Verificabilidad Automatizada y Calidad | Cobertura de pruebas automatizadas continua con 97 pruebas en pytest aprobadas en backend, 5 pruebas aprobadas en Flutter y análisis estático con 0 errores (`flutter analyze`). | `backend/tests/` (97 passed)<br>`mobile/test/` (5 passed)<br>`flutter analyze` (0 issues) | `TERMINADO_VERIFICADO` |
| **RNF12** | Coherencia de Diseño y Estándares UI/UX | Sistema de diseño unificado con tokens CSS Beige & Navy (`#14263D`, `#CCA77A`, `#FAF7F2`), componentes accesibles, microanimaciones reactivas, SVG nativos interactivos y jerarquía visual estandarizada. | `web/src/styles.css`<br>`mobile/lib/config/theme.dart`<br>`web/src/app/features/admin/reportes/` | `TERMINADO_VERIFICADO` |

---

## Detalle Técnico por Requisito No Funcional

### RNF01 — Seguridad y Control de Acceso
- **Autenticación:** Flujo OAuth2 Password Bearer con JSON Web Tokens. Se emite un `access_token` criptográfico con expiración de 30 minutos y un `refresh_token` de 7 días. La tabla `token_blacklist` revoca de forma persistente los tokens al cerrar sesión.
- **Autorización basada en roles (RBAC):** Se implementa la dependencia `require_permission` y el helper `get_current_active_user`. Los roles se diferencian estrictamente:
  - `is_platform_admin`: Administrador global SaaS (gestión de tenants, planes, respaldos de base de datos globales).
  - `Administrador de Tenant`: Administra exclusivamente los recursos de su propia empresa. Los accesos cruzados devuelven `HTTP 404 (Not Found)` para prevenir enumeración de recursos (IDOR).
  - `Encargado`: Acceso acotado a inventario, órdenes y catálogo de las sucursales asignadas.
  - `Cajero`: Operación de caja POS presencial.
  - `Cliente`: Catálogo, compras, reservas y seguimiento de pedidos propios.
- **Protección de Contraseñas:** Hashing unidireccional con algoritmo Bcrypt y sal única.

### RNF02 — Aislamiento Lógico de Datos Multi-tenant
- **Arquitectura de Base de Datos:** Base de datos relacional PostgreSQL con particionamiento por discriminador lógico `empresa_id` foráneo a la tabla `empresas(id)`.
- **Cobertura Integral:** Todas las tablas de negocio incluyen `empresa_id`: `usuarios`, `sucursales`, `productos`, `stock_inventario`, `carrito`, `orden_venta`, `envios`, `pagos`, `reservas`, `cambios_devolucion`, `favoritos`, `calificaciones`, `uploaded_files`, `proximamente` y `pruebas_virtuales`.
- **Garantía en Consultas:** Los endpoints y servicios resuelven el `empresa_id` directamente del JWT autenticado (`current_user.empresa_id`), impidiendo cualquier suplantación manual por parte del cliente HTTP.

### RNF03 — Durabilidad y Persistencia Local Offline
- **PWA (Angular 21):** Implementa `IndexedDbService` con almacén `stylestore_offline` conteniendo `catalogo`, `carrito_local`, `operaciones_pendientes` e `info_sincronizacion`.
- **Mobile (Flutter):** Implementa `SQLiteService` con base de datos local `stylestore.db`, conteniendo esquemas relacionales completos con claves foráneas para productos, variantes, clientes, ventas y cola de operaciones pendientes. Las operaciones resisten cierres forzados de la aplicación.

### RNF04 — Integridad Transaccional y Consistencia de Stock
- **Atomicidad ACID:** Las operaciones de venta en línea, checkout, y confirmación de reservas ejecutan bloques transaccionales con `SELECT ... FOR UPDATE` sobre la fila específica de `stock_inventario`.
- **Restricción de No Negatividad:** El modelo de datos y la capa de servicios validan `cantidad_disponible >= cantidad_solicitada`. En caso de falta de inventario, la transacción realiza un rollback íntegro y rechaza la operación sin efectos colaterales.

### RNF05 — Idempotencia en Operaciones y Sincronización
- **Contrato UUID:** Cada operación en cola (venta presencial o reserva) se genera en el cliente con un identificador UUID v4 único (`operacion_uuid`).
- **Mecanismo de Deduplicación:** El servicio `SyncService` consulta la existencia previa del `operacion_uuid` en la tabla `operaciones_sync`. Si la operación ya fue procesada, retorna la respuesta previa en caché sin volver a descontar stock ni duplicar registros contables.
- **Pagos:** `PagoService.confirmar` utiliza bloqueo de fila por `pago_id` garantizando un solo envío de correo y una sola notificación en la campana del cliente.

### RNF06 — Recuperación y Resolución de Conflictos (Refund)
- **Concurrencia de Última Unidad:** Si un cliente realiza una compra offline al contado y al recuperar conectividad el stock fue tomado por una transacción en línea previa, la sincronización marca la operación como `estado = "conflicto"` con motivo explícito `"Prenda no disponible: stock agotado por transacción previa"`.
- **Flujo de Reembolso:** Se crea automáticamente un registro auditable en `cambios_devolucion` / `reembolsos_pendientes` permitiendo a la caja devolver el importe en efectivo o acreditar saldo a favor al cliente.

### RNF07 — Mantenibilidad y Evolución de Esquemas (Alembic)
- **Migraciones Versionadas:** 14 migraciones secuenciales en `backend/alembic/versions/` con cabeza única `2d4e6f809123`.
- **Idempotencia DDL:** Verificación de existencia de tablas (`inspect(conn).has_table(...)`) que permite tanto la actualización limpia desde una base vacía como la coexistencia sobre bases preexistentes de semestres anteriores.

### RNF08 — Compatibilidad y Paridad Multiplataforma
- **Consumo de API:** Backend expone OpenAPI 3.1.0 documentado en `/docs`.
- **Mobile Dynamic Fallback:** `mobile/lib/config/api_config.dart` resuelve automáticamente el endpoint disponible (WiFi local, emulador Android `10.0.2.2` o nube Railway).
- **Web PWA:** Cumple con estándares W3C de Service Worker (`ngsw-worker.js`) y `manifest.webmanifest`.

### RNF09 — Rendimiento y Eficiencia
- **Tiempo de Respuesta:** Endpoints críticos de lectura de catálogo y consultas responden en menos de 100 ms en entorno de desarrollo.
- **Exportaciones Streaming:** Los reportes en Excel (`openpyxl`) y PDF (`reportlab`) se generan en memoria usando buffers de bytes (`io.BytesIO`) sin generar archivos temporales en disco que saturen el almacenamiento.
- **Machine Learning Determinista:** La regresión Ridge y el agrupamiento K-means implementados en `app/services/ml_service.py` operan sobre vectores sintéticos y ejecutan la predicción en < 20 ms sin sobrecarga de frameworks pesados.

### RNF10 — Observabilidad, Auditoría y Trazabilidad
- **Auditoría Global:** Toda operación administrativa sensible invoca `BitacoraService.registrar(...)` guardando usuario, rol, IP de origen, módulo afectado y detalle de la operación.
- **Rastreo GPS:** Los despachos generan un token único de seguimiento `TRK-XXXX` accesible públicamente para rastrear en tiempo real el vehículo y la distancia calculada mediante la fórmula geodésica de Haversine.

### RNF11 — Calidad de Software y Verificabilidad
- **Backend Tests:** 97 pruebas unitarias y de integración automáticas ejecutadas mediante `pytest -q`, cubriendo autenticación, aislamiento tenant, cálculo de reportes, conflictos de stock, reembolsos y modelos ML.
- **Mobile Tests:** 5 pruebas unitarias en Flutter (`flutter test --no-pub`) aprobadas.
- **Linting:** 0 errores en `flutter analyze --no-pub`.
- **Frontend Build:** Angular 21 compila en modo producción (`ng build`) generando un bundle optimizado (`main-S46ZNSZX.js`) sin advertencias bloqueantes.

### RNF12 — Coherencia de Diseño y Estándares UI/UX
- **Tokens Beige & Navy:**
  - Primario oscuro: `#14263D` (Navy institucional)
  - Acento dorado: `#CCA77A` / `#C8A97E` (Beige / Gold)
  - Fondo cálido: `#EEE7D8` / `#FAF7F2`
  - Tarjetas y contenedores: Glassmorphism y bordes sutiles `#D9D0BF`.
- **Gráficos SVG Interactivos:** Donut SVG nativo con cálculo de arcos `stroke-dasharray` para formas de pago y barras comparativas de sucursales con animación CSS.
