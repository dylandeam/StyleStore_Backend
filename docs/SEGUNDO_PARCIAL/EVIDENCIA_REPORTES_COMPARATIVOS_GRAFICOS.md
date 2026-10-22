# Evidencia de reportes comparativos, gráficos interactivos y aislamiento multi-tenant

Fecha: 22/10/2026.
Requisitos abordados: `REQ-039`, `REQ-040`, `REQ-063`.

## 1. Alcance implementado

### REQ-063 — Comparativa entre sucursales y aislamiento verificado
- **Endpoint backend dedicado**: `GET /api/v1/reportes/comparativa-sucursales/preview`, `/excel` y `/pdf`.
- **Métricas por sucursal**: Calcula para cada tienda del tenant autenticado ventas totales, porcentaje de participación en la facturación del tenant, cantidad de órdenes, ticket promedio, existencias consolidadas, ítems en stock crítico (`≤ 5` unidades), ítems agotados (`0` unidades), conteo de personal asignado y desglose de formas de pago (Efectivo, QR, PayPal).
- **Protección de frontera tenant (REQ-006 / REQ-007 / REQ-063)**: La función `_validate_report_sucursal` valida en todos los endpoints de reportes (`/ventas/preview`, `/ventas/excel`, `/ventas/pdf`, `/inventario/preview`, `/inventario/excel`, `/inventario/pdf`, `/dashboard-stats`, `/predicciones`, `/empleados/*`, `/devoluciones/*`, `/financiero/*`, `/caducidad/*`, `/compras/*`) que cualquier `sucursal_id` recibido pertenezca estrictamente al tenant activo del JWT. Si un usuario intenta sondear o filtrar por una sucursal de otra empresa, el servidor rechaza inmediatamente con `HTTP 404 (Not Found)`.
- **Exportables de comparativa**: Generación de archivo Excel (.xlsx) y PDF (.pdf) estilizados con la comparativa consolidada de todas las tiendas de la empresa.

### REQ-039 — Gráficos visuales interactivos y evidencia E2E
- **Web — Módulo Comparativo de Rendimiento**:
  - Resumen KPI superior: Sucursales activas, Gran Total Recaudado (Bs.), Órdenes Procesadas, Stock Consolidado, Alertas Críticas y Ticket Promedio General.
  - **Gráfico Comparativo de Participación**: Barras horizontales con degradado dorado (`#CCA77A` a `#C29B38`) proporcionales al volumen de ventas de cada sucursal con etiquetas de porcentaje y montos en Bs.
  - **Gráfico Comparativo de Inventario**: Barras con degradado navy (`#14263D` a `#315887`) relativas a la tienda con mayor existencia, con distintivos de stock crítico o stock óptimo y personal asignado.
  - Acciones de exportación directa a Excel y PDF con toast reactivo.
- **Web — Previsualización de Ventas**:
  - **Gráfico Donut SVG**: Distribución porcentual por método de pago (Efectivo, QR Simple, PayPal, Tarjetas) con arcos SVG calculados dinámicamente mediante `stroke-dasharray` y `stroke-dashoffset`, texto central con monto total y leyenda cromática.
  - **Ranking de Sucursales**: Distribución regional de ingresos con barras de progreso animadas.
- **Web — Previsualización de Inventario**:
  - **Medidor de Salud de Existencias**: Barra segmentada tricromática (Óptimo en verde `#2E7D32`, Crítico en dorado `#C29B38`, Agotado en rojo `#D32F2F`) y tarjetas analíticas de unidades.
  - **Existencias por Tienda**: Tarjetas con conteo total de existencias y advertencias destacadas de prendas en stock crítico.

### REQ-040 — Escenario reproducible multi-tenant para familias de reportes
- Batería de pruebas automatizadas reproducibles en `backend/tests/test_reportes_multiempresa_comparativa.py`:
  1. `test_reporte_ventas_aislamiento_multitenant`: Demuestra matemáticamente que el reporte de ventas de Tenant A excluye ventas millonarias de Tenant B y viceversa.
  2. `test_reporte_inventario_aislamiento_multitenant`: Comprueba que las existencias de Tenant A no exponen prendas ni catálogos de Tenant B.
  3. `test_comparativa_sucursales_metricas_y_aislamiento`: Comprueba la agregación side-by-side de las sucursales propias y la ausencia absoluta de sucursales ajenas.
  4. `test_rechazo_filtro_sucursal_ajena_404`: Comprueba que enviar `sucursal_id` de otro tenant a cualquier endpoint de ventas, inventario, empleados, finanzas o compras retorna `HTTP 404`.
  5. `test_familias_reportes_dinamicos_aisladas`: Comprueba que las familias dinámicas (Más Vendidos, Financiero, etc.) solo agregan registros de la empresa autenticada.

## 2. Validación técnica

- **Backend**:
  - `pytest -q`: **97 passed, 1 warning** (92 existentes + 5 nuevos).
  - Alembic head: `2d4e6f809123` (cabeza única preservada, esquema aditivo sin migraciones destructivas).
- **Web**:
  - `npm.cmd run build`: **Exitoso**, generación de bundle de producción `main-S46ZNSZX.js` y `styles-NKK3ZJ5P.css` sin errores tipográficos ni linter errors.
- **Mobile**:
  - `flutter analyze --no-pub`: **0 issues**.
  - `flutter test --no-pub`: **5 passed**.

## 3. Estado de requisitos tras la fase

| ID | Estado nuevo | Justificación |
|---|---|---|
| REQ-039 | TERMINADO_VERIFICADO | Gráficos SVG interactivos (Donut de formas de pago, ranking regional, medidor de salud de stock, barras comparativas de tiendas), previews y exportación Excel/PDF verificados localmente y cubiertos con tests. |
| REQ-040 | TERMINADO_VERIFICADO | Escenario multi-tenant reproducible automatizado (`test_reportes_multiempresa_comparativa.py`) para todas las familias de reportes. |
| REQ-063 | TERMINADO_VERIFICADO | Comparativa agregada entre sucursales de un mismo tenant con KPIs y rechazo `HTTP 404` ante sondas de sucursales ajenas comprobado en suite. |
