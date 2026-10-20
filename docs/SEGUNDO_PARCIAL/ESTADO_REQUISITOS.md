# Estado verificable de requisitos — segundo parcial

Este archivo es la copia versionada de seguimiento solicitada por el plan maestro. `TERMINADO_VERIFICADO` solo se usa cuando el criterio completo fue comprobado. `EN_CURSO` indica implementación parcial real; `EN_PRUEBAS`, código existente aún sin toda la evidencia manual/E2E; `PENDIENTE`, trabajo no iniciado o insuficiente.

| ID | Estado | Evidencia o pendiente principal |
|---|---|---|
| REQ-001 | TERMINADO_VERIFICADO | Inventario técnico versionado y contraste de los tres repositorios |
| REQ-002 | EN_PRUEBAS | Se extendió el proyecto existente; regresión automatizada completa, falta E2E desplegado |
| REQ-003 | EN_CURSO | Entidad `Empresa` y frontera tenant inicial; falta cubrir todo el dominio |
| REQ-004 | EN_CURSO | Migraciones aditivas para empresa, usuarios, sucursales y raíces de catálogo; ida/vuelta SQL comprobada, faltan recursos secundarios |
| REQ-005 | EN_CURSO | Empresa y sucursal son entidades separadas en backend; faltan UI web/móvil |
| REQ-006 | EN_CURSO | Aislamiento aplicado a usuarios, clientes, catálogo, stock, compras, ventas, pagos, carrito, envíos, cambios, bitácora y reportes; faltan recursos secundarios/archivos |
| REQ-007 | EN_CURSO | Tenant derivado del JWT y regresiones A/B para IDs directos, operaciones y exportables; falta auditoría completa de archivos/sync |
| REQ-008 | EN_PRUEBAS | JWT/refresh/blacklist/guards conservados; falta prueba manual de caída de red |
| REQ-009 | EN_PRUEBAS | Migración Alembic aditiva con una cabeza; falta aplicar/verificar en PostgreSQL desplegado |
| REQ-010 | PENDIENTE | Existe variante talla/color/sucursal, faltan precio por talla y medidas |
| REQ-011 | EN_PRUEBAS | Servidor autoritativo bloquea stock online y al sincronizar; reenvío UUID no duplica ni vuelve a descontar, falta prueba de concurrencia real |
| REQ-012 | PENDIENTE | No existe política/entidad completa de reembolso por rechazo offline |
| REQ-013 | TERMINADO_VERIFICADO | Contrato `/sync` versionado con UUID, tenant/usuario derivados del JWT, idempotencia, estados, motivo y pruebas de replay |
| REQ-014 | EN_CURSO | RBAC y bitácora existen; falta matriz tenant/sucursal/plan completa |
| REQ-015 | EN_PRUEBAS | Flujos preservados y suite aprobada; falta prueba manual desplegada |
| REQ-016 | EN_CURSO | PWA diferencia provisional/confirmado, bloquea QR offline y documenta límites; falta paridad móvil |
| REQ-017 | EN_CURSO | API crea empresa y administrador propio; falta asociación integral y UI |
| REQ-018 | TERMINADO_VERIFICADO | Existen exactamente Básico, Profesional y Personalizado; el tercero inicia sin beneficios inventados y es editable |
| REQ-019 | EN_CURSO | Mínimos y límites oficiales viven en backend; falta aplicar bloqueos de capacidad/sucursales a las operaciones |
| REQ-020 | TERMINADO_VERIFICADO | Precio, moneda, límites, capacidades, beneficios y estilo se configuran en backend y UI por ámbito global/tenant |
| REQ-021 | EN_CURSO | Alta, cambio, consulta, estado, inicio/vencimiento y snapshot implementados; faltan renovación y bloqueos operativos |
| REQ-022 | EN_CURSO | Contratación/cambio simulado disponible para cliente; falta flujo administrativo de renovación SaaS |
| REQ-023 | EN_PRUEBAS | Manifest, Service Worker, app shell y actualización controlada generan correctamente; falta evidencia manual de instalación/carga offline desplegada |
| REQ-024 | EN_PRUEBAS | IndexedDB persiste catálogo y cola comercial aislada por empresa/usuario; falta prueba E2E de reinicio de navegador |
| REQ-025 | EN_PRUEBAS | Catálogo con precios, variantes y stock conocido cae a snapshot local y muestra fecha/advertencia; falta E2E en navegador |
| REQ-026 | EN_PRUEBAS | Reserva offline persiste con UUID, comprobante provisional y sincronización; falta E2E de cierre/reapertura |
| REQ-027 | EN_PRUEBAS | POS guarda venta de contado con detalle/importes y bloquea QR offline; falta E2E de comprobante impreso |
| REQ-028 | EN_PRUEBAS | Pantalla PWA muestra cola y estados pendiente/confirmada/rechazada/conflicto con motivo; falta evidencia visual E2E |
| REQ-029 | EN_PRUEBAS | Flutter conserva Provider/secure storage e integra SQLite con claves foráneas; falta prueba en dispositivo de cierre/reapertura |
| REQ-030 | EN_PRUEBAS | SQLite guarda catálogo, sucursales, ventas/detalles, reservas/detalles y cola con claves foráneas; prueba de reapertura aprobada, falta clientes mínimos y dispositivo real |
| REQ-031 | EN_PRUEBAS | Flutter consulta catálogo/stock conocido y registra reservas y ventas de contado offline; falta demostración completa en modo avión |
| REQ-032 | EN_PRUEBAS | Flutter muestra cola/resultados y sincroniza reservas/ventas al reconectar; falta evidencia en dispositivo |
| REQ-033 | EN_PRUEBAS | Web y móvil conservan colas UUID y transiciones sin borrar fallos; falta E2E de proceso interrumpido en dispositivo |
| REQ-034 | EN_PRUEBAS | PWA/Flutter reintentan y backend confirma idempotentemente ventas/reservas; falta simulación E2E de timeout real |
| REQ-035 | EN_PRUEBAS | Prueba automatizada confirma que la última unidad solo genera una venta, la reserva competidora queda en conflicto, el reintento conserva el motivo y el stock queda en cero; falta E2E con dos dispositivos |
| REQ-036 | EN_PRUEBAS | Backend deriva tenant del JWT; IndexedDB y SQLite separan cola por empresa+usuario y las pruebas locales rechazan lectura desde otro ámbito; falta evidencia A/B en dispositivos |
| REQ-037 | EN_PRUEBAS | La interfaz acepta consultas escritas y voz nativa con manejo de incompatibilidad; backend exige rol administrativo y plan con IA, falta evidencia de micrófono en navegador real |
| REQ-038 | EN_PRUEBAS | El contexto IA consulta ventas, sucursales, envíos e inventario reales restringidos al tenant; prueba A/B impide incorporar operaciones ajenas, faltan filtros conversacionales E2E |
| REQ-039 | EN_CURSO | Tablas/exportación Excel/PDF y prueba negativa A/B existen; faltan gráficos y evidencia E2E completa |
| REQ-040 | EN_PRUEBAS | Existen más de cuatro familias de reporte; falta escenario reproducible multiempresa |
| REQ-041 | EN_PRUEBAS | IA restringida por tenant, rol, contratación vigente y capacidad configurable; pregunta/respuesta tienen límites validados y pruebas Básico/Profesional, falta batería de solicitudes ambiguas/maliciosas |
| REQ-042 | PENDIENTE | Dataset sintético ML reproducible no implementado |
| REQ-043 | PENDIENTE | Modelo supervisado no implementado |
| REQ-044 | PENDIENTE | Modelo no supervisado no implementado |
| REQ-045 | PENDIENTE | Integración ML/dashboard no implementada |
| REQ-046 | EN_PRUEBAS | Recomendaciones y vestidor preservados; falta E2E desplegado |
| REQ-047 | EN_CURSO | Hay pruebas base; faltan evidencias completas RNF01–RNF12 |
| REQ-048 | EN_PRUEBAS | Backend y PWA verificados públicamente tras push; APK release con SQLite generado y validado por hash, falta instalación/validación móvil real |
| REQ-049 | PENDIENTE | Artefactos ICONIX/UML 2.5+ del segundo parcial no creados |
| REQ-050 | PENDIENTE | Documento final capítulos I–VI no disponible |
| REQ-051 | EN_CURSO | 61 pruebas backend, conflicto de última unidad/replay sync, tenant/planes A/B, build/test PWA, 5 pruebas Flutter incluida reapertura SQLite y auditoría runtime aprobados; faltan E2E en dispositivo |
| REQ-052 | EN_CURSO | Matriz iniciada; paquetes/capturas de entregas pendientes |
| REQ-053 | PENDIENTE | QR y enlaces finales verificados no preparados |
| REQ-054 | EN_CURSO | Solicitudes de cambio existen; falta nueva nota vinculada completa |
| REQ-055 | EN_CURSO | Cambios/devoluciones existen; falta sector y efectos completos |
| REQ-056 | PENDIENTE | Email idempotente por pago confirmado no comprobado |
| REQ-057 | EN_CURSO | Notificaciones existen; falta evento de pago con deduplicación |
| REQ-058 | EN_CURSO | Reservas cliente/staff y límite de 3 días existen; falta cierre tenant integral |
| REQ-059 | EN_PRUEBAS | Horario configurable por sucursal y hora de retiro validados en API/web/móvil; faltan franjas libres/ocupadas y E2E |
| REQ-060 | PENDIENTE | Precio por talla no implementado |
| REQ-061 | PENDIENTE | Medidas de prenda/variante no implementadas |
| REQ-062 | PENDIENTE | Traspasos entre sucursales no implementados |
| REQ-063 | EN_CURSO | Filtros por sucursal existen; falta aislamiento tenant/comparación verificada |
| REQ-064 | PENDIENTE | Calificaciones poscompra no implementadas |
| REQ-065 | PENDIENTE | Favoritos/lista de deseos no implementados |
| REQ-066 | EN_CURSO | Bloqueo online de stock existe; falta mensaje uniforme y conflicto offline |
| REQ-067 | PENDIENTE | Flujo auditable de reembolso offline no implementado |
| REQ-068 | PENDIENTE | Requiere propuesta del equipo sin desplazar obligatorios |
| REQ-069 | EN_CURSO | Contratos compartidos preservados; offline/paridad nueva pendientes |
| REQ-070 | EN_CURSO | Operaciones sync conservan estado, motivo, recurso resultante y fechas; faltan métricas/alertas agregadas |
| REQ-071 | EN_PRUEBAS | Banner global informa conexión, catálogo cacheado, última sincronización, pendientes y actualización PWA; falta E2E visual |
| REQ-072 | EN_CURSO | Caché y cola web están separadas por empresa+usuario; falta estrategia equivalente SQLite móvil |

## Decisiones bloqueadas explícitamente

- Los tres planes serán configurables desde administración; el tercer plan no tendrá beneficios inventados y recibirá sus valores mediante configuración administrativa.
- “Horario de reserva” queda definido como fecha y hora de recogida dentro del horario de atención de la sucursal, con máximo de 3 días. Falta completar franjas libres/ocupadas antes de cerrar REQ-059.
- Un commit local no demuestra despliegue: REQ-048/053 necesitan push, pipeline y comprobación de URL/APK.
