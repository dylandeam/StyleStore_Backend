# Estado verificable de requisitos — segundo parcial

Este archivo es la copia versionada de seguimiento solicitada por el plan maestro. `TERMINADO_VERIFICADO` solo se usa cuando el criterio completo fue comprobado. `EN_CURSO` indica implementación parcial real; `EN_PRUEBAS`, código existente aún sin toda la evidencia manual/E2E; `PENDIENTE`, trabajo no iniciado o insuficiente.

| ID | Estado | Evidencia o pendiente principal |
|---|---|---|
| REQ-001 | TERMINADO_VERIFICADO | Inventario técnico versionado y contraste de los tres repositorios |
| REQ-002 | TERMINADO_VERIFICADO | Extensión aditiva del proyecto existente con regresión automatizada completa de backend y suites Flutter/Web aprobadas; conteo vigente en `AUDITORIA_INTEGRAL_2026-10-22.md` |
| REQ-003 | TERMINADO_VERIFICADO | Entidad `Empresa`, consola SaaS maestra y frontera tenant aplicada a catálogo, archivos, próximos lanzamientos y probador virtual |
| REQ-004 | TERMINADO_VERIFICADO | Cadena Alembic aditiva con cabeza única `4f6a8b012345`; reparación idempotente de deriva Railway desplegada y reservas restauradas sin pérdida de datos |
| REQ-005 | TERMINADO_VERIFICADO | Empresa y sucursal son entidades separadas; la consola web y el perfil móvil muestran jerarquía, planes, estado, asignación de sucursal con resiliencia offline en SQLite |
| REQ-006 | TERMINADO_VERIFICADO | Aislamiento estricto multi-tenant en recursos principales y secundarios; respaldos exclusivos de admin y rechazo HTTP 404 ante referencias cruzadas comprobado en suite |
| REQ-007 | TERMINADO_VERIFICADO | Tenant derivado obligatoriamente del JWT; pruebas A/B en test_tenant_foundation.py y test_secondary_tenant_security.py confirman cero fuga de datos |
| REQ-008 | TERMINADO_VERIFICADO | Autenticación robusta JWT, refresh tokens, blacklist y guards RBAC verificados en test_auth.py y test_bitacora_security.py |
| REQ-009 | TERMINADO_VERIFICADO | Cabecera lineal única `4f6a8b012345`; smoke desplegado confirma modelos críticos sincronizados (reservas, catálogo, pagos, notificaciones y sync) |
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
| REQ-022 | TERMINADO_VERIFICADO | Renovación auditada y administración formal de planes sin overrides simulados inseguros; el 25/10/2026 una orden oficial PayPal Sandbox cambió de Básico a Intermedio únicamente después de captura `COMPLETED` por USD 18.18 (Bs 200 a 11 BOB/USD) |
| REQ-023 | TERMINADO_VERIFICADO | Web App Manifest ('standalone', 'es-BO'), Service Worker ngsw y app shell prefetch generados y comprobados en build de producción y ngsw.json |
| REQ-024 | TERMINADO_VERIFICADO | IndexedDB 'stylestore-offline' con stores 'catalog' y 'operations' aislados por ámbito empresa+usuario ('${empresaId}:${usuarioId}') |
| REQ-025 | TERMINADO_VERIFICADO | Catálogo y ficha offline con precios, variantes y stock conocido desde snapshots SQLite; imágenes persistentes en caché de disco y advertencia visual con fecha de sincronización, verificado en Samsung (`mobile@66ef919`) |
| REQ-026 | TERMINADO_VERIFICADO | Reservas offline con UUID cliente v4, comprobante provisional 'LOCAL-XXXXXXXX' y sincronización diferida idempotente |
| REQ-027 | TERMINADO_VERIFICADO | POS offline con ventas de contado en efectivo, detalle e importes, y bloqueo estricto de pagos electrónicos/QR verificado en suite |
| REQ-028 | TERMINADO_VERIFICADO | Pantalla PWA (/cuenta/operaciones-pendientes) con estados pendiente/sincronizando/confirmada/rechazada/conflicto y motivo |
| REQ-029 | TERMINADO_VERIFICADO | Flutter conserva Provider/secure storage, integra SQLite con claves foráneas y restaura sesión. Firebase Android/Admin y FCM fueron verificados en Samsung físico con la app abierta, en segundo plano y cerrada; el envío remoto devolvió `SENT=1` y Android publicó la alerta sin actividad visible |
| REQ-030 | TERMINADO_VERIFICADO | Base de datos SQLite 'stylestore_offline.db' con foreign keys activas, tablas relacionales (catalog, branches, clients, queue, details) y 9 tests aprobados |
| REQ-031 | TERMINADO_VERIFICADO | Catálogo, detalle e imagen cacheada comprobados físicamente sin Wi-Fi/datos en Samsung; UI advierte stock provisional y fecha del snapshot local (`mobile@66ef919`) |
| REQ-032 | TERMINADO_VERIFICADO | Cola offline y recuperación automática de conectividad con sincronización en segundo plano verificada en Flutter y Android |
| REQ-033 | TERMINADO_VERIFICADO | Web y móvil conservan colas UUID y transiciones sin borrar fallos; el carrito móvil añade/persiste prendas offline y las elimina de su cola solo tras sincronización exitosa (`mobile@66ef919`) |
| REQ-034 | TERMINADO_VERIFICADO | Reintentos idempotentes y confirmación de ventas/reservas garantizando una sola ejecución física comprobados en test_sync.py |
| REQ-035 | TERMINADO_VERIFICADO | Prueba de carrera en test_sync.py confirma: última unidad asignada a venta, reserva competidora en conflicto, stock en cero sin sobreventa |
| REQ-036 | TERMINADO_VERIFICADO | Derivación obligatoria de tenant y usuario desde el JWT; rechazo HTTP 403 ante colisión cruzada de UUIDs verificado en suite |
| REQ-037 | TERMINADO_VERIFICADO | Consultas por texto/voz Web Speech (es-BO), Groq real desplegado y fallback local explícito; producción devolvió `online_groq/ia_powered=true` y la regresión de caída confirmó `online_local/reglas_locales` |
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
| REQ-051 | TERMINADO_VERIFICADO | Suite continua de seguridad, multiempresa, stock, idempotencia, ML, reportes, pagos, IA híbrida y push; cierre del 25/10/2026 con 132 casos backend, 2 web y 14 Flutter aprobados |
| REQ-052 | TERMINADO_VERIFICADO | Paquetes oficiales para las 4 entregas (25/10, 01/11, 08/11 y defensa 10/11 a las 07:00) estructurados y documentados en `PAQUETES_ENTREGAS_OFICIALES.md` |
| REQ-053 | TERMINADO_VERIFICADO | Enlaces de despliegue Vercel/Railway/GitHub verificados y 3 códigos QR SVG generados y documentados en `ENLACES_Y_QR_OFICIALES.md` |
| REQ-054 | TERMINADO_VERIFICADO | Solicitud y liquidación de cambio generan nota vinculada NCJ-, ajustan inventario y conservan diferencia monetaria o saldo a favor |
| REQ-055 | TERMINADO_VERIFICADO | Cambios/devoluciones con plazo configurable por tenant, cobro o saldo a favor, reembolso, sucursal y auditoría por tenant |
| REQ-056 | TERMINADO_VERIFICADO | Todo pago aprobado genera correo una sola vez mediante bloqueo de fila y marca persistente; SMTP Gmail está protegido en Railway y el 24/10/2026 se comprobó entrega externa real de correo transaccional y confirmación de contraseña |
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
| REQ-069 | TERMINADO_VERIFICADO | Paridad Web-Mobile en contratos offline, cola SQLite/IndexedDB, banner reactivo y métricas; prueba física móvil cerró detalle, imágenes, carrito, reconexión y bloqueo seguro de checkout (`mobile@66ef919`) |
| REQ-070 | TERMINADO_VERIFICADO | Diagnóstico estructurado y métricas agregadas de sincronización implementadas en `GET /sync/metricas` y servicio web, documentado con tests en `EVIDENCIA_DIAGNOSTICO_SYNC_Y_STOCK.md` |
| REQ-071 | TERMINADO_VERIFICADO | Banner global reactivo informa sin conexión, catálogo cacheado con fecha, operaciones pendientes con enlace a cola y actualización Service Worker PWA |
| REQ-072 | TERMINADO_VERIFICADO | Aislamiento por empresa+usuario en SQLite móvil v2, carrito pendiente protegido, limpieza segura y diagnósticos; 14 pruebas Flutter y sincronización física aprobadas (`mobile@66ef919`) |
| REQ-073 | TERMINADO_VERIFICADO | Vencimiento marca la contratación como vencida e inactiva el tenant; la renovación exclusiva para admin exige captura PayPal `COMPLETED`. Verificado E2E en Railway/PayPal Sandbox: contrato anterior reemplazado, nuevo Intermedio pagado/activo y tenant activo |
| REQ-074 | TERMINADO_VERIFICADO | Redistribución predictiva compara ventas y cobertura por variante entre sucursales del tenant, limita el origen al 50 %, conserva reserva de demanda, descuenta traspasos pendientes y abre el flujo humano de revisión/aprobación; verificado en `test_inventory_transfers.py` y build Angular |

## Decisiones bloqueadas explícitamente

- Los tres planes serán configurables desde administración; el tercer plan no tendrá beneficios inventados y recibirá sus valores mediante configuración administrativa.
- “Horario de reserva” está implementado con franjas libres/ocupadas y exclusión concurrente; conservar pruebas de regresión antes de modificar la agenda.
- Un commit local no demuestra despliegue: PayPal/FCM y REQ-048/053 requieren pipeline, credenciales externas y comprobación física/URL.
- PayPal, FCM y SMTP cuentan con evidencia externa real en Sandbox/dispositivo/correo; no se usaron mocks para cerrar REQ-022, REQ-029, REQ-056 ni REQ-073.
