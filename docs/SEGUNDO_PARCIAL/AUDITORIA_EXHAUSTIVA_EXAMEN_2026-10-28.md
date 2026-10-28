# Auditoría exhaustiva contra el examen — 28/10/2026

> **Corrección de auditoría (28/10/2026).** La primera versión de este documento sobrevaloró la existencia de servicios y colas internas como evidencia de que el requisito era utilizable. La prueba desde la interfaz encontró dos brechas obligatorias: la reserva móvil estaba escondida en un icono y no podía elegir horario sin red; la caja web tenía cola offline, pero no podía recuperar sucursales e inventario al perder conexión. Ambas se corrigieron en código y pruebas locales. Permanecen abiertas hasta completar el humo físico en Samsung y navegador instalado; por ello este documento ya no declara el proyecto al 100 %.

## Fuente y criterio de cierre

Fuente primaria: `D:\Descargas\Examen Parcial-2 - Sistemas 2 - S2-2026.pdf` (12 páginas).

Esta auditoría no considera una pantalla o un texto de documentación como prueba suficiente. Un requisito se marca:

- **Verificado**: existe implementación trazable y prueba automatizada o evidencia física vigente.
- **Implementado, requiere humo externo**: el código y las pruebas locales existen, pero depende de navegador, dispositivo o servicio cloud.
- **Mejora adicional**: no es una obligación textual del examen, pero convierte la analítica en una decisión operativa real.

## Hallazgo principal

El traspaso de stock entre sucursales **no aparece como obligación literal** en el PDF. El examen sí exige integrar modelos, generar reportes inteligentes, desarrollar un dashboard y permitir interpretar resultados (páginas 5–7). El proyecto tenía el traspaso manual y las alertas predictivas por separado, pero no conectaba ambos procesos. Esa era una brecha funcional real: se mostraba el análisis, pero no se podía convertir directamente en una redistribución revisable.

Se cerró con una recomendación tenant-safe por producto, color y talla que:

1. compara ventas reales de los últimos 30 días entre sucursales;
2. detecta baja cobertura en la sucursal destino;
3. selecciona como origen una sucursal con menor velocidad de venta y excedente;
4. nunca propone más del 50 % del stock efectivo del origen;
5. conserva una reserva mínima de 14 días de demanda en el origen;
6. descuenta traspasos pendientes de entrada y salida para no recomendar dos veces las mismas unidades;
7. requiere la capacidad de plan `predicciones`;
8. abre el flujo existente de revisión y aprobación: la IA recomienda, pero no mueve inventario sola.

## Matriz de requisitos obligatorios

| Fuente | Requisito comprobado | Estado | Evidencia principal |
|---|---|---|---|
| Págs. 1–2 | Evolución del prototipo, no reemplazo de tecnologías | Verificado | Repositorios FastAPI, Angular y Flutter conservados; no se sustituyó el stack |
| Pág. 3 | PWA instalable | Verificado | `web/ngsw-config.json`, manifest y build Angular de producción |
| Pág. 3 | Recursos offline y consulta de catálogo cacheado | Verificado | `web/src/app/core/services/offline-db.service.ts`, `carrito.service.ts` |
| Pág. 3 | Precios, tallas, colores y stock conocido offline | Verificado | snapshot de catálogo web y SQLite móvil; pruebas de detalle y catálogo local |
| Pág. 3 | Reserva offline | Verificado en Samsung y Railway | Acción visible, franjas provisionales locales, persistencia tras reinicio y operación `2CE4042B` confirmada por `/sync` al reconectar |
| Pág. 3 | Venta de contado offline | Implementado, prueba física pendiente | Caja web conserva sucursales e inventario, limita a efectivo, genera ticket provisional y usa `queueCashSale`; Flutter conserva su pantalla offline |
| Pág. 3 | Cola persistente y estados visibles | Verificado | ruta `/cuenta/operaciones-pendientes`, SQLite/IndexedDB; estados pendiente, sincronizando, confirmado, rechazado y conflicto |
| Págs. 3–4 | Una operación no desaparece al fallar el envío | Verificado | `offline-db.service.ts`, `offline_sync_service.dart`, pruebas de preservación y reintento |
| Pág. 4 | Flutter con SQLite e integridad referencial | Verificado | `mobile/lib/services/local_database_service.dart`; pruebas de reapertura, ámbitos y detalles |
| Pág. 4 | Catálogo, sucursales, clientes mínimos, ventas, reservas y detalles locales | Verificado | esquema SQLite y 16 pruebas Flutter aprobadas el 28/10/2026 |
| Pág. 4 | UUID, tenant, sucursal, reintento, idempotencia y conflictos | Verificado | modelos y servicio `sync`, pruebas `test_sync.py` y `test_sync_metricas_conflicto.py` |
| Págs. 4–5 | Venta offline con detalle, precios, total, pago y estado | Verificado | contrato `venta_efectivo`, persistencia local y confirmación central transaccional |
| Pág. 5 | Solo contado sin conexión | Verificado localmente | bloqueo explícito de PayPal/QR offline en web y móvil; falta repetir humo de navegador instalado |
| Pág. 5 | Cambios de prendas dentro de plazo | Verificado | módulo de cambios/devoluciones, plazo configurable por tenant y pruebas en `test_v6_features.py` |
| Págs. 5–6 | Reporte por lenguaje natural escrito | Verificado | `/reportes/asistente-ia`, `report_ai_service.py`, Groq con fallback local |
| Pág. 5 | Entrada verbal | Implementado, requiere humo externo | Web Speech `es-BO`; depende del permiso y compatibilidad del navegador |
| Págs. 5–6 | Fechas, sucursales, categorías y productos | Verificado | interpretación controlada y contexto operacional tenant-scoped |
| Págs. 5–6 | Datos reales, más de una tabla, tablas o gráficos | Verificado | reportes de ventas, inventario, productos, clientes, envíos, devoluciones, financiero y comparativa |
| Pág. 6 | Al menos cuatro tipos de reporte variables | Verificado | existen más de cuatro familias con preview, Excel y PDF; pruebas multiempresa |
| Pág. 6 | Solicitudes ambiguas/no soportadas y consultas controladas | Verificado | validación de consulta, límites de entrada y respuestas locales controladas |
| Págs. 6–7 | Datos sintéticos y preprocesamiento | Verificado | `generate_synthetic_sales`, semilla fija y pruebas de reproducibilidad |
| Pág. 6 | Modelo supervisado y evaluación | Verificado | regresión ridge, R² y MAE comprobados en `test_ml_predictions.py` |
| Pág. 6 | Modelo no supervisado y evaluación | Verificado | segmentación K-means reproducible y pruebas de grupos RFM |
| Pág. 6 | Integración, reportes inteligentes y dashboard | Verificado | `/reportes/predicciones`, dashboard analítico y alertas de stock |
| Págs. 6–7 | IA sin acceso arbitrario a BD | Verificado | la IA recibe un contexto preparado por servicios; no ejecuta SQL generado por el modelo |
| Págs. 7–8 | PostgreSQL compartido con aislamiento lógico | Verificado | `empresa_id`, scope derivado del JWT y pruebas A/B multi-tenant |
| Pág. 7 | Tenant distinto de sucursal | Verificado | `Empresa` 1:N `Sucursal`, servicios y pruebas de pertenencia |
| Pág. 7 | Administrar empresas, admin, usuarios y sucursales | Verificado | consola SaaS, tenant admin, asociaciones y pruebas de límites |
| Págs. 7–8 | Plan, suscripción, vigencia, cambio y restricciones | Verificado | `PlanService`, capacidades, vencimiento y renovación; PayPal Sandbox supera lo mínimo exigido |
| Pág. 8 | Límites de planes configurables desde backend | Verificado | catálogo de planes editable y enforcement backend |
| Pág. 8 | Mínimo dos empresas independientes | Verificado | pruebas multiempresa crean y aíslan tenants A/B |
| Págs. 8–9 | RNF01–RNF12 | Verificado con observaciones | evidencia específica en `EVIDENCIA_RNF01_RNF12.md`; la compatibilidad/servicios externos siempre requieren humo del entorno de defensa |
| Pág. 10 | Stack obligatorio | Verificado | FastAPI, Angular PWA, IndexedDB, Flutter/Dart, SQLite, PostgreSQL, REST, IA y UML 2.5+ |
| Págs. 11–12 | Documento por capítulos, ICONIX, pruebas y anexos | Verificado | `DOCUMENTO_FINAL_CAPITULOS_I_VI.md`, `ARTEFACTOS_ICONIX_UML25.md` y paquetes de entrega |

## Trazabilidad del nuevo flujo de redistribución

| Capa | Evidencia |
|---|---|
| Backend | `app/services/ml_service.py::transfer_recommendations` |
| API | `GET /api/v1/reportes/recomendaciones-traspaso-stock` |
| Seguridad | tenant del JWT, validación de sucursal y capacidad `predicciones` |
| Ejecución | `POST /api/v1/inventario/traspasos` y aprobación transaccional existente |
| Web Angular | `features/admin/inventario/inventario.component.*` |
| Pruebas | `tests/test_inventory_transfers.py` cubre cantidad recomendada, reserva, traspaso pendiente y bloqueo por plan |

## Qué no debe presentarse como “terminado” sin una prueba de entorno

- instalación PWA y voz deben probarse en el navegador elegido para la defensa;
- PayPal, SMTP, Groq, FCM y Railway dependen de credenciales y disponibilidad externa;
- la recepción push debe validarse con la aplicación abierta, en segundo plano y cerrada;
- el despliegue solo queda cerrado cuando Railway/Vercel contienen los commits y pasan un humo contra sus URLs públicas.

## Resultado de regresión local del 28/10/2026

- Backend: pruebas específicas de reserva **22/22 aprobadas**; la regresión completa debe conservar su comprobante de ejecución antes del cierre.
- Web: **16 pruebas aprobadas** y build de producción correcto, incluida recuperación offline de sucursales e inventario POS.
- Flutter: **19 pruebas aprobadas**, incluidas persistencia SQLite, franjas de retiro y serialización de fecha compatible con el contrato central.

## Conclusión

No corresponde afirmar todavía que el proyecto está al 100 %. La revisión estática encontró gran parte de la arquitectura, pero la prueba de accesibilidad real descubrió brechas que esa revisión no detectó. El cierre exige demostrar, desde las pantallas finales, reserva móvil offline, venta web de contado offline, persistencia después de reiniciar, sincronización idempotente al reconectar y resolución visible de conflictos. Solo después de esas evidencias se puede cambiar su estado a **Verificado**.
