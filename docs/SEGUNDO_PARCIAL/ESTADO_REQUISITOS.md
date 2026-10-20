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
| REQ-011 | EN_CURSO | Checkout online bloquea stock; falta flujo offline y conflictos sync |
| REQ-012 | PENDIENTE | No existe política/entidad completa de reembolso por rechazo offline |
| REQ-013 | PENDIENTE | No existe contrato común de sincronización |
| REQ-014 | EN_CURSO | RBAC y bitácora existen; falta matriz tenant/sucursal/plan completa |
| REQ-015 | EN_PRUEBAS | Flujos preservados y suite aprobada; falta prueba manual desplegada |
| REQ-016 | PENDIENTE | Falta UX/documentación completa de alcance offline |
| REQ-017 | EN_CURSO | API crea empresa y administrador propio; falta asociación integral y UI |
| REQ-018 | PENDIENTE | Tercer plan requiere definición; no se inventaron beneficios |
| REQ-019 | PENDIENTE | Límites y capacidades por plan no implementados |
| REQ-020 | PENDIENTE | Configuración backend de planes no implementada |
| REQ-021 | PENDIENTE | Ciclo de suscripción no implementado |
| REQ-022 | PENDIENTE | Simulación de contratación/renovación no implementada |
| REQ-023 | PENDIENTE | Angular aún no tiene Service Worker PWA |
| REQ-024 | PENDIENTE | No existe IndexedDB comercial |
| REQ-025 | PENDIENTE | Catálogo PWA offline no implementado |
| REQ-026 | PENDIENTE | Reserva PWA offline no implementada |
| REQ-027 | PENDIENTE | Venta de contado PWA offline no implementada |
| REQ-028 | PENDIENTE | UI de cola/estados PWA no implementada |
| REQ-029 | PENDIENTE | Flutter no incluye SQLite |
| REQ-030 | PENDIENTE | Esquema SQLite local no implementado |
| REQ-031 | PENDIENTE | Operaciones Flutter offline no implementadas |
| REQ-032 | PENDIENTE | UI y recuperación sync Flutter no implementadas |
| REQ-033 | PENDIENTE | Colas persistentes con UUID no implementadas |
| REQ-034 | PENDIENTE | Replay idempotente general no implementado |
| REQ-035 | PENDIENTE | Resolución de conflicto offline no implementada |
| REQ-036 | PENDIENTE | Caches/sync todavía no existen para probar aislamiento |
| REQ-037 | EN_CURSO | Reportes escritos y aislamiento tenant existen; falta voz y autorización por plan |
| REQ-038 | EN_CURSO | Filtros controlados, datos reales y ámbito tenant aplicados; falta autorización por plan y validación E2E |
| REQ-039 | EN_CURSO | Tablas/exportación Excel/PDF y prueba negativa A/B existen; faltan gráficos y evidencia E2E completa |
| REQ-040 | EN_PRUEBAS | Existen más de cuatro familias de reporte; falta escenario reproducible multiempresa |
| REQ-041 | PENDIENTE | Falta restricción por tenant y plan para IA |
| REQ-042 | PENDIENTE | Dataset sintético ML reproducible no implementado |
| REQ-043 | PENDIENTE | Modelo supervisado no implementado |
| REQ-044 | PENDIENTE | Modelo no supervisado no implementado |
| REQ-045 | PENDIENTE | Integración ML/dashboard no implementada |
| REQ-046 | EN_PRUEBAS | Recomendaciones y vestidor preservados; falta E2E desplegado |
| REQ-047 | EN_CURSO | Hay pruebas base; faltan evidencias completas RNF01–RNF12 |
| REQ-048 | EN_PRUEBAS | URLs/remotos declarados; falta verificar despliegue posterior a estos commits |
| REQ-049 | PENDIENTE | Artefactos ICONIX/UML 2.5+ del segundo parcial no creados |
| REQ-050 | PENDIENTE | Documento final capítulos I–VI no disponible |
| REQ-051 | EN_CURSO | 56 pruebas backend y regresiones tenant A/B aprobadas; faltan offline/sync/planes y E2E desplegado |
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
| REQ-070 | PENDIENTE | Diagnóstico estructurado de sync no implementado |
| REQ-071 | PENDIENTE | Indicador de conexión/último sync no implementado |
| REQ-072 | PENDIENTE | Estrategia de caché/cola por usuario-tenant no implementada |

## Decisiones bloqueadas explícitamente

- Los tres planes serán configurables desde administración; el tercer plan no tendrá beneficios inventados y recibirá sus valores mediante configuración administrativa.
- “Horario de reserva” queda definido como fecha y hora de recogida dentro del horario de atención de la sucursal, con máximo de 3 días. Falta completar franjas libres/ocupadas antes de cerrar REQ-059.
- Un commit local no demuestra despliegue: REQ-048/053 necesitan push, pipeline y comprobación de URL/APK.
