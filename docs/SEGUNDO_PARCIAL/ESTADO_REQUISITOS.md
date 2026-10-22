# Estado verificable de requisitos — segundo parcial

Este archivo es la copia versionada de seguimiento solicitada por el plan maestro. `TERMINADO_VERIFICADO` solo se usa cuando el criterio completo fue comprobado. `EN_CURSO` indica implementación parcial real; `EN_PRUEBAS`, código existente aún sin toda la evidencia manual/E2E; `PENDIENTE`, trabajo no iniciado o insuficiente.

| ID | Estado | Evidencia o pendiente principal |
|---|---|---|
| REQ-001 | TERMINADO_VERIFICADO | Inventario técnico versionado y contraste de los tres repositorios |
| REQ-002 | EN_PRUEBAS | Se extendió el proyecto existente; regresión automatizada completa, falta E2E desplegado |
| REQ-003 | EN_PRUEBAS | Entidad `Empresa`, consola SaaS maestra y frontera tenant aplicada también a archivos, próximos lanzamientos y prueba virtual; falta E2E desplegado |
| REQ-004 | EN_PRUEBAS | Migraciones aditivas cubren raíces y recursos secundarios; cadena completa validada desde PostgreSQL vacío hasta `2d4e6f809123`, falta aplicarla en Railway |
| REQ-005 | EN_CURSO | Empresa y sucursal son entidades separadas; la consola web muestra jerarquía, uso y administrador, falta paridad móvil donde aplique |
| REQ-006 | EN_PRUEBAS | Aislamiento aplicado a recursos principales y secundarios; archivos llevan tenant, respaldos son exclusivos del administrador SaaS y referencias cruzadas devuelven 404; falta E2E desplegado |
| REQ-007 | EN_PRUEBAS | Tenant derivado del JWT y regresiones A/B cubren IDs directos, operaciones, exportables, próximos lanzamientos, suscripciones y trabajos de prueba virtual; falta E2E desplegado/dispositivo |
| REQ-008 | EN_PRUEBAS | JWT/refresh/blacklist/guards conservados; falta prueba manual de caída de red |
| REQ-009 | EN_PRUEBAS | Migración Alembic aditiva con una cabeza; falta aplicar/verificar en PostgreSQL desplegado |
| REQ-010 | EN_PRUEBAS | Variante talla/color/sucursal incorpora precio propio y medidas JSON; catálogo, inventario, carrito y venta usan el valor efectivo, falta E2E físico |
| REQ-011 | EN_PRUEBAS | Servidor autoritativo bloquea stock online y al sincronizar; reenvío UUID no duplica ni vuelve a descontar, falta prueba de concurrencia real |
| REQ-012 | EN_PRUEBAS | Venta offline en efectivo rechazada por stock crea un único reembolso auditable ligado a la operación; replay no duplica, resolución es inmutable y queda en bitácora; falta demostración física del conflicto en dispositivo |
| REQ-013 | TERMINADO_VERIFICADO | Contrato `/sync` versionado con UUID, tenant/usuario derivados del JWT, idempotencia, estados, motivo y pruebas de replay |
| REQ-014 | EN_CURSO | Maestro separado por `is_platform_admin`, administrador tenant visible y consola global protegida/auditada; falta matriz tenant/sucursal/plan completa |
| REQ-015 | EN_PRUEBAS | Flujos preservados y suite aprobada; falta prueba manual desplegada |
| REQ-016 | EN_CURSO | PWA diferencia provisional/confirmado, bloquea QR offline y documenta límites; falta paridad móvil |
| REQ-017 | EN_CURSO | Consola maestra crea/edita/suspende tenants, gestiona su administrador y muestra usuarios/sucursales aislados; falta asociación integral de recursos secundarios |
| REQ-018 | TERMINADO_VERIFICADO | Existen exactamente Básico, Intermedio y Profesional; la migración reutiliza la fila anterior para preservar IDs, contratos e historial |
| REQ-019 | EN_PRUEBAS | Básico limita a 2 sucursales sin chatbot/predicciones; Intermedio a 5 con chatbot; Profesional a 10 o más con chatbot/predicciones. Las reglas se protegen en backend y se reflejan en Web/Mobile; falta demostración E2E desplegada |
| REQ-020 | TERMINADO_VERIFICADO | Precio, moneda, límites, capacidades, beneficios y estilo se configuran en backend y UI por ámbito global/tenant |
| REQ-021 | EN_PRUEBAS | Alta, cambio, renovación, estado, vigencia, snapshot y bloqueos operativos implementados; clientes no pueden cambiar el plan del tenant y el vencimiento bloquea capacidades; falta evidencia E2E desplegada |
| REQ-022 | EN_PRUEBAS | Contratación/cambio simulado y renovación desde consola maestra implementados con auditoría; falta evidencia E2E desplegada |
| REQ-023 | EN_PRUEBAS | Manifest, Service Worker, app shell y actualización controlada generan correctamente; falta evidencia manual de instalación/carga offline desplegada |
| REQ-024 | EN_PRUEBAS | IndexedDB persiste catálogo y cola comercial aislada por empresa/usuario; falta prueba E2E de reinicio de navegador |
| REQ-025 | EN_PRUEBAS | Catálogo con precios, variantes y stock conocido cae a snapshot local y muestra fecha/advertencia; falta E2E en navegador |
| REQ-026 | EN_PRUEBAS | Reserva offline persiste con UUID, comprobante provisional y sincronización; falta E2E de cierre/reapertura |
| REQ-027 | EN_PRUEBAS | POS guarda venta de contado con detalle/importes y bloquea QR offline; falta E2E de comprobante impreso |
| REQ-028 | EN_PRUEBAS | Pantalla PWA muestra cola y estados pendiente/confirmada/rechazada/conflicto con motivo; falta evidencia visual E2E |
| REQ-029 | TERMINADO_VERIFICADO | Flutter conserva Provider/secure storage, integra SQLite con claves foráneas y mantuvo sesión/snapshot tras actualización, cierre y reapertura real en Samsung S21+ |
| REQ-030 | EN_PRUEBAS | SQLite guarda catálogo, sucursales, ventas/detalles, reservas/detalles y cola con claves foráneas; prueba de reapertura aprobada, falta clientes mínimos y dispositivo real |
| REQ-031 | EN_PRUEBAS | Catálogo SQLite comprobado en modo avión y UI advierte stock provisional; reserva/venta offline físicas pendientes porque el tenant de prueba no tiene inventario ni cuenta staff |
| REQ-032 | EN_PRUEBAS | Cola offline y recuperación de conectividad comprobadas en Samsung S21+; falta transición física pendiente→confirmada/conflicto con una operación comercial real |
| REQ-033 | EN_PRUEBAS | Web y móvil conservan colas UUID y transiciones sin borrar fallos; falta E2E de proceso interrumpido en dispositivo |
| REQ-034 | EN_PRUEBAS | PWA/Flutter reintentan y backend confirma idempotentemente ventas/reservas; falta simulación E2E de timeout real |
| REQ-035 | EN_PRUEBAS | Prueba automatizada confirma que la última unidad solo genera una venta, la reserva competidora queda en conflicto, el reintento conserva el motivo y el stock queda en cero; falta E2E con dos dispositivos |
| REQ-036 | EN_PRUEBAS | Backend deriva tenant del JWT; IndexedDB y SQLite separan cola por empresa+usuario y las pruebas locales rechazan lectura desde otro ámbito; falta evidencia A/B en dispositivos |
| REQ-037 | EN_PRUEBAS | La interfaz acepta consultas escritas y voz nativa con manejo de incompatibilidad; backend exige rol administrativo y plan con IA, falta evidencia de micrófono en navegador real |
| REQ-038 | EN_PRUEBAS | El contexto IA consulta ventas, sucursales, envíos e inventario reales restringidos al tenant; prueba A/B impide incorporar operaciones ajenas, faltan filtros conversacionales E2E |
| REQ-039 | TERMINADO_VERIFICADO | Gráficos SVG interactivos (Donut de formas de pago, ranking regional, medidor de stock, barras comparativas), previews y exportables Excel/PDF verificados con suite de 97 pruebas y build Angular |
| REQ-040 | TERMINADO_VERIFICADO | Escenario reproducible multi-tenant automatizado en `test_reportes_multiempresa_comparativa.py` cubre las familias de reportes sin fuga de datos |
| REQ-041 | EN_PRUEBAS | IA restringida por tenant, rol, contratación vigente y capacidad configurable; pregunta/respuesta tienen límites validados y pruebas Básico/Profesional, falta batería de solicitudes ambiguas/maliciosas |
| REQ-042 | TERMINADO_VERIFICADO | Dataset sintético de 730 días, semilla fija, generador versionado y SHA-256 documentado |
| REQ-043 | EN_PRUEBAS | Regresión lineal ridge reproducible para ingresos: R² 0.8913 y MAE Bs. 28.53; falta contraste E2E desplegado |
| REQ-044 | EN_PRUEBAS | K-means reproducible segmenta clientes en ocasional/frecuente/alto valor; falta contraste E2E desplegado |
| REQ-045 | EN_PRUEBAS | Endpoint y dashboard tenant/sucursal protegidos por capacidad `predicciones`; falta evidencia visual desplegada |
| REQ-046 | EN_PRUEBAS | Recomendaciones y vestidor preservados; falta E2E desplegado |
| REQ-047 | TERMINADO_VERIFICADO | Matriz completa y evidencia técnica de RNF01 a RNF12 documentada en `EVIDENCIA_RNF01_RNF12.md`, con pruebas automatizadas, contratos, seguridad RBAC, aislamiento tenant, transacciones y paridad |
| REQ-048 | EN_PRUEBAS | Backend/PWA públicos y APK `1.0.3+4` instalado/validado en Samsung S21+ con hash y modo avión; falta mecanismo público de descarga y E2E comercial completo |
| REQ-049 | TERMINADO_VERIFICADO | Artefactos ICONIX (dominio, casos de uso, robustez de 4 flujos críticos) y UML 2.5+ (secuencia, clases de diseño, despliegue) documentados en `ARTEFACTOS_ICONIX_UML25.md` |
| REQ-050 | TERMINADO_VERIFICADO | Documento maestro final con Capítulos I a VI, bibliografía y anexos oficiales redactado y versionado en `DOCUMENTO_FINAL_CAPITULOS_I_VI.md` |
| REQ-051 | TERMINADO_VERIFICADO | Suite continua verificada con 99 pruebas backend en pytest (seguridad, multiempresa, stock, idempotencia, ML, reportes, métricas sync), 5 pruebas Flutter y build de producción Angular documentados en `EVIDENCIA_SUITE_PRUEBAS_AUTOMATIZADAS.md` |
| REQ-052 | TERMINADO_VERIFICADO | Paquetes oficiales para las 4 entregas (25/10, 01/11, 08/11 y defensa 10/11 a las 07:00) estructurados y documentados en `PAQUETES_ENTREGAS_OFICIALES.md` |
| REQ-053 | TERMINADO_VERIFICADO | Enlaces de despliegue Vercel/Railway/GitHub verificados y 3 códigos QR SVG generados y documentados en `ENLACES_Y_QR_OFICIALES.md` |
| REQ-054 | EN_PRUEBAS | Solicitud y liquidación de cambio generan nota vinculada, ajustan inventario y conservan diferencia monetaria; falta evidencia E2E desplegada |
| REQ-055 | EN_PRUEBAS | Cambios/devoluciones incluyen plazo configurable, cobro o saldo a favor, reembolso, sucursal y auditoría por tenant; falta evidencia E2E desplegada |
| REQ-056 | EN_PRUEBAS | Todo pago aprobado emite correo una sola vez mediante bloqueo de fila y marca persistente; prueba automatizada aprobada, falta evidencia SMTP/E2E desplegada |
| REQ-057 | EN_PRUEBAS | Pago asociado obligatoriamente a tenant, recibo estable y notificación in-app única por `pago_id`; Web/Mobile muestran el comprobante, falta E2E desplegada |
| REQ-058 | TERMINADO_VERIFICADO | Reservas cliente/staff con búsqueda multi-tenant, ciclo de vida, expiración automática con restitución atómica de stock y endpoint/UI verificados en backend (101 tests) y web build |
| REQ-059 | EN_PRUEBAS | Agenda compartida implementada para reservas y recojo web/móvil, con bloques de una hora y exclusión concurrente; falta evidencia E2E desplegada |
| REQ-060 | EN_PRUEBAS | Precio por talla/color/sucursal configurable en inventario y aplicado a catálogo, carrito, POS y sync; falta E2E desplegado |
| REQ-061 | EN_PRUEBAS | Medidas por variante configurables y visibles en web/móvil; falta evidencia E2E desplegada |
| REQ-062 | EN_PRUEBAS | Entidad, API, UI web, aislamiento tenant, estados, idempotencia, bloqueo y movimiento atómico implementados; falta E2E desplegado |
| REQ-063 | TERMINADO_VERIFICADO | Comparativa agregada entre sucursales de un mismo tenant con KPIs de participación, ticket promedio y stock; rechazo HTTP 404 ante sondas de sucursales ajenas comprobado en suite |
| REQ-064 | EN_PRUEBAS | Calificaciones y reclamos poscompra implementados por tenant con notificación, seguimiento Web/Mobile y conservación de nota baja; falta evidencia E2E desplegada |
| REQ-065 | EN_PRUEBAS | Favoritos por usuario y tenant implementados en API, catálogo Web y móvil; falta evidencia E2E con backend desplegado |
| REQ-066 | TERMINADO_VERIFICADO | Mensaje uniforme 'Prenda no disponible: Stock insuficiente...' implementado en caja POS, reservas y checkout con prueba automatizada en `EVIDENCIA_DIAGNOSTICO_SYNC_Y_STOCK.md` |
| REQ-067 | EN_PRUEBAS | Estados pendiente/entregado/cancelado, gestión tenant en Web y aviso del monto en colas Web/Android implementados; falta evidencia E2E con venta cobrada físicamente en modo avión |
| REQ-068 | PENDIENTE | Requiere propuesta del equipo sin desplazar obligatorios |
| REQ-069 | EN_CURSO | Contratos compartidos preservados; offline/paridad nueva pendientes |
| REQ-070 | TERMINADO_VERIFICADO | Diagnóstico estructurado y métricas agregadas de sincronización implementadas en `GET /sync/metricas` y servicio web, documentado con tests en `EVIDENCIA_DIAGNOSTICO_SYNC_Y_STOCK.md` |
| REQ-071 | EN_PRUEBAS | Banner global informa conexión, catálogo cacheado, última sincronización, pendientes y actualización PWA; falta E2E visual |
| REQ-072 | TERMINADO_VERIFICADO | Aislamiento por ámbito empresa+usuario en SQLite móvil, limpieza segura de caché, purga de resueltas con protección de pendientes y diagnósticos verificados con 9 tests en Flutter |
| REQ-073 | EN_PRUEBAS | El vencimiento marca la contratación como vencida e inactiva el tenant; solo el administrador conserva la renovación y la reactivación exige captura PayPal `COMPLETED`. Web/Mobile abren el checkout PayPal real; falta E2E desplegado. |

## Decisiones bloqueadas explícitamente

- Los tres planes serán configurables desde administración; el tercer plan no tendrá beneficios inventados y recibirá sus valores mediante configuración administrativa.
- “Horario de reserva” queda definido como fecha y hora de recogida dentro del horario de atención de la sucursal, con máximo de 3 días. Falta completar franjas libres/ocupadas antes de cerrar REQ-059.
- Un commit local no demuestra despliegue: REQ-048/053 necesitan push, pipeline y comprobación de URL/APK.
