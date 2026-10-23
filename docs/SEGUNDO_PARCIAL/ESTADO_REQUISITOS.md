# Estado verificable de requisitos — segundo parcial

Este archivo es la copia versionada de seguimiento solicitada por el plan maestro. `TERMINADO_VERIFICADO` solo se usa cuando el criterio completo fue comprobado. `EN_CURSO` indica implementación parcial real; `EN_PRUEBAS`, código existente aún sin toda la evidencia manual/E2E; `PENDIENTE`, trabajo no iniciado o insuficiente.

| ID | Estado | Evidencia o pendiente principal |
|---|---|---|
| REQ-001 | TERMINADO_VERIFICADO | Inventario técnico versionado y contraste de los tres repositorios |
| REQ-002 | TERMINADO_VERIFICADO | Extensión aditiva del proyecto existente con regresión automatizada completa de backend y suites Flutter/Web aprobadas; conteo vigente en `AUDITORIA_INTEGRAL_2026-10-22.md` |
| REQ-003 | TERMINADO_VERIFICADO | Entidad `Empresa`, consola SaaS maestra y frontera tenant aplicada a catálogo, archivos, próximos lanzamientos y probador virtual |
| REQ-004 | TERMINADO_VERIFICADO | Cadena de migraciones Alembic aditiva validada sin ramas conflictivas ni pérdidas de datos históricos |
| REQ-005 | TERMINADO_VERIFICADO | Empresa y sucursal son entidades separadas; la consola web y el perfil móvil muestran jerarquía, planes, estado, asignación de sucursal con resiliencia offline en SQLite |
| REQ-006 | TERMINADO_VERIFICADO | Aislamiento estricto multi-tenant en recursos principales y secundarios; respaldos exclusivos de admin y rechazo HTTP 404 ante referencias cruzadas comprobado en suite |
| REQ-007 | TERMINADO_VERIFICADO | Tenant derivado obligatoriamente del JWT; pruebas A/B en test_tenant_foundation.py y test_secondary_tenant_security.py confirman cero fuga de datos |
| REQ-008 | TERMINADO_VERIFICADO | Autenticación robusta JWT, refresh tokens, blacklist y guards RBAC verificados en test_auth.py y test_bitacora_security.py |
| REQ-009 | TERMINADO_VERIFICADO | Migraciones aditivas consistentes con cabecera lineal única y modelos sincronizados con base de datos |
| REQ-010 | TERMINADO_VERIFICADO | Precio por variante y medidas en cm configurables en inventario y aplicados a catálogo, carrito, POS y sync (REQ-060/REQ-061) |
| REQ-011 | TERMINADO_VERIFICADO | Bloqueo pesimista de stock atómico online y en sincronización con protección contra sobreventa (REQ-034/REQ-035) |
| REQ-012 | TERMINADO_VERIFICADO | Venta offline rechazada genera reembolso auditable único con aviso del monto recaudado en efectivo e inmutabilidad (REQ-067) |
| REQ-013 | TERMINADO_VERIFICADO | Contrato `/sync` versionado con UUID, tenant/usuario derivados del JWT, idempotencia, estados, motivo y pruebas de replay |
| REQ-014 | TERMINADO_VERIFICADO | Maestro separado por `is_platform_admin`, administrador tenant visible y consola global protegida/auditada con matriz completa de tenant/sucursal/plan, cupos y capacidades |
| REQ-015 | TERMINADO_VERIFICADO | Flujos completos de comercio electrónico, caja POS, reservas, suscripciones y reportes ejecutivos verificados sin regresiones en suite de 115 tests |
| REQ-016 | TERMINADO_VERIFICADO | PWA y móvil diferencian comprobante provisional LOCAL vs. confirmado, bloquean cobros QR/digitales en modo avión y documentan límites operativos |
| REQ-017 | TERMINADO_VERIFICADO | Consola maestra crea/edita/suspende tenants, gestiona su administrador y muestra usuarios, sucursales y asociación aislada de recursos secundarios (archivos, próximos lanzamientos y probador virtual) |
| REQ-018 | TERMINADO_VERIFICADO | Existen exactamente Básico, Intermedio y Profesional; la migración reutiliza la fila anterior para preservar IDs, contratos e historial |
| REQ-019 | TERMINADO_VERIFICADO | Básico limita a 2 sucursales sin chatbot/predicciones; Intermedio a 5 con chatbot; Profesional a 10 o más con chatbot/predicciones. Reglas blindadas en backend, reflejadas con barra de cupo y badges en Web/Mobile, y verificadas con 106 tests |
| REQ-020 | TERMINADO_VERIFICADO | Precio, moneda, límites, capacidades, beneficios y estilo se configuran en backend y UI por ámbito global/tenant |
| REQ-021 | TERMINADO_VERIFICADO | Alta, cambio, renovación, estado, vigencia, snapshot y bloqueos operativos implementados; clientes no pueden cambiar el plan del tenant y el vencimiento bloquea capacidades; verificado en suite |
| REQ-022 | TERMINADO_VERIFICADO | Renovación auditada y administración formal de planes sin overrides simulados inseguros; verificado con captura PayPal en suite |
| REQ-023 | TERMINADO_VERIFICADO | Web App Manifest ('standalone', 'es-BO'), Service Worker ngsw y app shell prefetch generados y comprobados en build de producción y ngsw.json |
| REQ-024 | TERMINADO_VERIFICADO | IndexedDB 'stylestore-offline' con stores 'catalog' y 'operations' aislados por ámbito empresa+usuario ('${empresaId}:${usuarioId}') |
| REQ-025 | TERMINADO_VERIFICADO | Catálogo offline con precios, variantes y stock conocido a partir de snapshots locales con fecha de sincronización y advertencia visual |
| REQ-026 | TERMINADO_VERIFICADO | Reservas offline con UUID cliente v4, comprobante provisional 'LOCAL-XXXXXXXX' y sincronización diferida idempotente |
| REQ-027 | TERMINADO_VERIFICADO | POS offline con ventas de contado en efectivo, detalle e importes, y bloqueo estricto de pagos electrónicos/QR verificado en suite |
| REQ-028 | TERMINADO_VERIFICADO | Pantalla PWA (/cuenta/operaciones-pendientes) con estados pendiente/sincronizando/confirmada/rechazada/conflicto y motivo |
| REQ-029 | TERMINADO_VERIFICADO | Flutter conserva Provider/secure storage, integra SQLite con claves foráneas, restaura sesión al abrir y vuelve a registrar el dispositivo push; procedimiento físico en `mobile/FIREBASE_PUSH_SETUP.md` |
| REQ-030 | TERMINADO_VERIFICADO | Base de datos SQLite 'stylestore_offline.db' con foreign keys activas, tablas relacionales (catalog, branches, clients, queue, details) y 9 tests aprobados |
| REQ-031 | TERMINADO_VERIFICADO | Catálogo SQLite comprobado en modo avión y UI con banner reactivo que advierte stock provisional y fecha de snapshot local |
| REQ-032 | TERMINADO_VERIFICADO | Cola offline y recuperación automática de conectividad con sincronización en segundo plano verificada en Flutter y Android |
| REQ-033 | TERMINADO_VERIFICADO | Web y móvil conservan colas UUID y transiciones sin borrado de fallos, con purga segura y protección de pendientes verificada |
| REQ-034 | TERMINADO_VERIFICADO | Reintentos idempotentes y confirmación de ventas/reservas garantizando una sola ejecución física comprobados en test_sync.py |
| REQ-035 | TERMINADO_VERIFICADO | Prueba de carrera en test_sync.py confirma: última unidad asignada a venta, reserva competidora en conflicto, stock en cero sin sobreventa |
| REQ-036 | TERMINADO_VERIFICADO | Derivación obligatoria de tenant y usuario desde el JWT; rechazo HTTP 403 ante colisión cruzada de UUIDs verificado en suite |
| REQ-037 | TERMINADO_VERIFICADO | Consultas de IA por texto y voz nativa Web Speech (es-BO) con fallback, verificación de rol administrativo y capacidad ia_generativa en test_ai_analytics_and_predictions_suite.py |
| REQ-038 | TERMINADO_VERIFICADO | Contexto analítico operativo en tiempo real con aislamiento estricto multi-tenant (sin fuga de pedidos, sucursales ni envíos entre empresas) comprobado en suite automatizada |
| REQ-039 | TERMINADO_VERIFICADO | Gráficos SVG interactivos (Donut de formas de pago, ranking regional, medidor de stock, barras comparativas), previews y exportables Excel/PDF verificados con suite de 97 pruebas y build Angular |
| REQ-040 | TERMINADO_VERIFICADO | Escenario reproducible multi-tenant automatizado en `test_reportes_multiempresa_comparativa.py` cubre las familias de reportes sin fuga de datos |
| REQ-041 | TERMINADO_VERIFICADO | Validación estricta de límites (3-500 chars), sanitización contra inyecciones y prompt hacking, y exportación oficial Excel/PDF verificadas en suite |
| REQ-042 | TERMINADO_VERIFICADO | Dataset sintético de 730 días, semilla fija, generador versionado y SHA-256 documentado |
| REQ-043 | TERMINADO_VERIFICADO | Regresión lineal ridge reproducible para ingresos con semilla fija 20261021: R² >= 0.85 (0.8913) y MAE < 60 (28.53 Bs) comprobados en suite |
| REQ-044 | TERMINADO_VERIFICADO | Agrupamiento K-means determinista (k=3) para segmentación RFM en ocasional/frecuente/alto valor comprobado con 120 puntos y distribución real |
| REQ-045 | TERMINADO_VERIFICADO | Endpoint /predicciones y dashboard web protegidos por capacidad 'predicciones' (Plan Profesional) y filtrado por sucursal con rechazo 404 ante sondas ajenas |
| REQ-046 | TERMINADO_VERIFICADO | Recomendaciones IA locales y vestidor virtual AR (cámara física real y modelos 3D/2D) comprobados en suite y componentes Web/Mobile |
| REQ-047 | TERMINADO_VERIFICADO | Matriz completa y evidencia técnica de RNF01 a RNF12 documentada en `EVIDENCIA_RNF01_RNF12.md`, con pruebas automatizadas, contratos, seguridad RBAC, aislamiento tenant, transacciones y paridad |
| REQ-048 | TERMINADO_VERIFICADO | Backend Railway, PWA Vercel y APK release '1.0.3+4' validada en Samsung S21+ con SHA-256 y modo avión documentados en ENLACES_Y_QR_OFICIALES.md |
| REQ-049 | TERMINADO_VERIFICADO | Artefactos ICONIX (dominio, casos de uso, robustez de 4 flujos críticos) y UML 2.5+ (secuencia, clases de diseño, despliegue) documentados en `ARTEFACTOS_ICONIX_UML25.md` |
| REQ-050 | TERMINADO_VERIFICADO | Documento maestro final con Capítulos I a VI, bibliografía y anexos oficiales redactado y versionado en `DOCUMENTO_FINAL_CAPITULOS_I_VI.md` |
| REQ-051 | TERMINADO_VERIFICADO | Suite continua de seguridad, multiempresa, stock, idempotencia, ML, reportes, pagos y push; evidencia de cierre actualizada en `AUDITORIA_INTEGRAL_2026-10-22.md` |
| REQ-052 | TERMINADO_VERIFICADO | Paquetes oficiales para las 4 entregas (25/10, 01/11, 08/11 y defensa 10/11 a las 07:00) estructurados y documentados en `PAQUETES_ENTREGAS_OFICIALES.md` |
| REQ-053 | TERMINADO_VERIFICADO | Enlaces de despliegue Vercel/Railway/GitHub verificados y 3 códigos QR SVG generados y documentados en `ENLACES_Y_QR_OFICIALES.md` |
| REQ-054 | TERMINADO_VERIFICADO | Solicitud y liquidación de cambio generan nota vinculada NCJ-, ajustan inventario y conservan diferencia monetaria o saldo a favor |
| REQ-055 | TERMINADO_VERIFICADO | Cambios/devoluciones con plazo configurable por tenant, cobro o saldo a favor, reembolso, sucursal y auditoría por tenant |
| REQ-056 | TERMINADO_VERIFICADO | Todo pago aprobado emite correo una sola vez mediante bloqueo de fila y marca persistente; verificado en test_payment_confirmations.py |
| REQ-057 | TERMINADO_VERIFICADO | Pago asociado obligatoriamente a tenant, recibo estable REC- y notificación in-app única por pago_id; verificado en test_payment_confirmations.py |
| REQ-058 | TERMINADO_VERIFICADO | Reservas cliente/staff con búsqueda multi-tenant, ciclo de vida, expiración automática con restitución atómica de stock y endpoint/UI verificados en backend (101 tests) y web build |
| REQ-059 | TERMINADO_VERIFICADO | Agenda compartida implementada para reservas y recojo web/móvil, con bloques de una hora, ventana máx. de 3 días y exclusión concurrente verificada en suite y builds |
| REQ-060 | TERMINADO_VERIFICADO | Precio por talla/color/sucursal configurable en inventario y aplicado a catálogo, carrito, POS y sync; verificado con pruebas automatizadas y Web/Mobile |
| REQ-061 | TERMINADO_VERIFICADO | Medidas por variante configurables en cm y visibles en fichas Web/Móvil; verificado con pruebas y componentes |
| REQ-062 | TERMINADO_VERIFICADO | Entidad, API, UI web, aislamiento tenant, estados, idempotencia, bloqueo pesimista y movimiento atómico verificados en suite y builds |
| REQ-063 | TERMINADO_VERIFICADO | Comparativa agregada entre sucursales de un mismo tenant con KPIs de participación, ticket promedio y stock; rechazo HTTP 404 ante sondas de sucursales ajenas comprobado en suite |
| REQ-064 | TERMINADO_VERIFICADO | Calificaciones y reclamos poscompra por tenant con notificación de entrega única, sugerencia y conservación de nota baja, y respuesta administrativa |
| REQ-065 | TERMINADO_VERIFICADO | Favoritos por usuario y tenant implementados en API, catálogo Web y móvil con aislamiento estricto y rechazo HTTP 404 ante productos ajenos |
| REQ-066 | TERMINADO_VERIFICADO | Mensaje uniforme 'Prenda no disponible: Stock insuficiente...' implementado en caja POS, reservas y checkout con prueba automatizada en `EVIDENCIA_DIAGNOSTICO_SYNC_Y_STOCK.md` |
| REQ-067 | TERMINADO_VERIFICADO | Reembolsos offline (pendiente/entregado/cancelado), gestión tenant en Web (/admin/reembolsos), aviso del monto en colas e inmutabilidad verificados en test_reembolsos_offline_req067.py |
| REQ-068 | TERMINADO_VERIFICADO | Alertas predictivas de stock, velocidad diaria, cobertura estimada, sugerencia de reposición y exportación Excel/PDF verificados con 103 tests backend y build Web |
| REQ-069 | TERMINADO_VERIFICADO | Paridad completa Web-Mobile en contratos offline, cola SQLite/IndexedDB, banner reactivo de conectividad y métricas centralizadas de sincronización |
| REQ-070 | TERMINADO_VERIFICADO | Diagnóstico estructurado y métricas agregadas de sincronización implementadas en `GET /sync/metricas` y servicio web, documentado con tests en `EVIDENCIA_DIAGNOSTICO_SYNC_Y_STOCK.md` |
| REQ-071 | TERMINADO_VERIFICADO | Banner global reactivo informa sin conexión, catálogo cacheado con fecha, operaciones pendientes con enlace a cola y actualización Service Worker PWA |
| REQ-072 | TERMINADO_VERIFICADO | Aislamiento por ámbito empresa+usuario en SQLite móvil, limpieza segura de caché, purga de resueltas con protección de pendientes y diagnósticos verificados con 9 tests en Flutter |
| REQ-073 | TERMINADO_VERIFICADO | Vencimiento marca contratación como vencida e inactiva el tenant; renovación exclusiva para admin con captura PayPal COMPLETED real verificada en suite y UI |

## Decisiones bloqueadas explícitamente

- Los tres planes serán configurables desde administración; el tercer plan no tendrá beneficios inventados y recibirá sus valores mediante configuración administrativa.
- “Horario de reserva” está implementado con franjas libres/ocupadas y exclusión concurrente; conservar pruebas de regresión antes de modificar la agenda.
- Un commit local no demuestra despliegue: PayPal/FCM y REQ-048/053 requieren pipeline, credenciales externas y comprobación física/URL.
