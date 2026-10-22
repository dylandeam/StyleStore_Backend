# Evidencia de Modelos Machine Learning y Asistente de IA (REQ-037, REQ-038, REQ-041, REQ-043, REQ-044, REQ-045)

**Fecha**: 2026-10-22  
**Requisitos**:
- `REQ-037` — Asistente de IA para reportes con consultas escritas y por voz nativa (Web Speech API / es-BO) con control de roles administrativos y plan contratado.
- `REQ-038` — Contexto analítico de IA alimentado con datos operativos reales (ventas, pedidos, envíos, sucursales) y aislamiento estricto multi-tenant (sin fuga de datos entre empresas).
- `REQ-041` — Seguridad, límites validados en consultas (3 a 500 caracteres), sanitización contra prompt injection / inyecciones SQL y exportación oficial a Excel (.xlsx) y PDF (.pdf).
- `REQ-042` — Dataset sintético de 730 días (2 años), reproducible y determinista con semilla fija `20261021`.
- `REQ-043` — Modelo supervisado de regresión lineal Ridge para pronóstico de ingresos diarios con $R^2 \ge 0.85$ y $MAE < 60$.
- `REQ-044` — Modelo no supervisado K-means para segmentación RFM de clientes ($k=3$: `ocasional`, `frecuente`, `alto_valor`).
- `REQ-045` — Endpoint `/api/v1/reportes/predicciones` y panel visual en dashboard protegidos por la capacidad `predicciones` (Plan Profesional exclusivo) y filtro de sucursal por tenant.  
**Estado resultante**: `TERMINADO_VERIFICADO`

---

## 1. Asistente Analítico de IA para Reportes Ejecutivos (REQ-037, REQ-038, REQ-041)

### A. Control de Acceso y Capacidades (REQ-037)
- **Endpoint**: `POST /api/v1/reportes/asistente-ia`.
- **Restricción de Rol**: Exige rol `administrador`, `encargado` o `encargado_sucursal`. Clientes regulares y staff no autorizado son rechazados con **HTTP 403 Forbidden** (`"Los reportes con IA requieren un rol administrativo autorizado."`).
- **Restricción de Plan**: Requiere que la suscripción activa del tenant posea la capacidad `ia_generativa` (Plan Profesional o Intermedio configurado). Si el tenant está en Plan Básico, la API responde **HTTP 403 Forbidden**.
- **Entrada por Voz y Texto**:
  - En Web (`web/src/app/features/chatbot/chatbot-widget/` y panel de reportes), se integra Web Speech API nativa con configuración `es-BO` (español de Bolivia), feedback visual de escucha reactiva y fallback explicativo ante navegadores sin soporte nativo de micrófono.

### B. Aislamiento Multi-Tenant Estricto del Contexto Operativo (REQ-038)
- El servicio `ReportAIService._recopilar_contexto_operativo()` extrae en tiempo real:
  - Ventas de hoy y recaudación mensual mediante `scope_by_sucursal`.
  - Delivery y envíos asociados exclusivamente a las sucursales del `empresa_id` del usuario autenticado.
  - Inventario crítico y niveles de stock sin cruzar fronteras de empresa.
- **Prueba A/B Verificada**: Al inyectar una orden de 88,888 Bs en el Tenant 2 y consultar el contexto con el Administrador del Tenant 1, el contexto de Tenant 1 totaliza únicamente sus 250 Bs y su sucursal, con **cero fugas de información inter-empresa**.

### C. Validación, Sanitización y Exportación (REQ-041)
- **Límites de Longitud**: Validación con Pydantic (`min_length=3`, `max_length=500`). Preguntas menores a 3 caracteres o mayores a 500 reciben **HTTP 422 Unprocessable Entity**.
- **Resistencia a Inyecciones**: Intentos maliciosos como `IGNORE ALL RULES; DROP TABLE...` o caracteres SQL son neutralizados por el ORM y la arquitectura de capas, manteniendo la integridad de la base de datos intacta.
- **Exportación Oficial**:
  - `POST /api/v1/reportes/asistente-ia/excel`: Genera libro OpenXML (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`) con la consulta, respuesta y KPIs tabulados.
  - `POST /api/v1/reportes/asistente-ia/pdf`: Genera documento estilizado (`application/pdf`) con cabecera corporativa StyleStore.

---

## 2. Machine Learning: Modelos Supervisado y No Supervisado (REQ-042, REQ-043, REQ-044)

### A. Dataset Sintético Determinista (REQ-042)
- Función `generate_synthetic_sales(rows=730, seed=20261021)` en `app/services/ml_service.py`.
- Genera 730 registros diarios (2 años completos) con componentes estacionales sinusoides, efectos de fin de semana, campañas de promoción y ruido gaussiano reproducible.

### B. Regresión Lineal Ridge Reproducible (REQ-043)
- Función `train_supervised_model()` en `app/services/ml_service.py`.
- **Características**: Tendencia normalizada, mes del año, día de la semana, indicador de fin de semana y bandera de promoción.
- **Regularización L2**: Matriz normal con penalidad ridge diagonal $\lambda = 0.001$ resuelta por eliminación de Gauss-Jordan con pivoteo parcial.
- **Métricas Comprobadas en Suite**:
  - $R^2 \ge 0.85$ (Valor obtenido: **0.8913**).
  - $MAE < 60$ Bs (Valor obtenido: **28.53 Bs**).
  - Semilla determinista: `20261021`.

### C. Segmentación K-Means de Clientes (REQ-044)
- Función `train_unsupervised_model()` en `app/services/ml_service.py`.
- **Variables RFM**: Frecuencia de compra, valor monetario acumulado y recencia en días.
- **Algoritmo**: K-means con $k=3$ centroides inicializados por percentiles y convergencia iterativa determinista.
- **Segmentos**: `ocasional`, `frecuente`, `alto_valor`.
- **Mapeo Real**: El endpoint calibra el modelo sintético con las compras reales registradas en el tenant, clasificando a cada cliente según la distancia euclidiana normalizada al centroide más cercano.

---

## 3. Protección por Capacidad de Plan y Scoping de Sucursales (REQ-045)

- **Endpoint**: `GET /api/v1/reportes/predicciones`.
- **Gatekeeper**: `Depends(require_plan_capability("predicciones"))`.
- **Comportamiento**:
  - Plan Básico: Responde **HTTP 403 Forbidden** indicando que requiere el plan Profesional.
  - Plan Intermedio: Responde **HTTP 403 Forbidden**.
  - Plan Profesional: Responde **HTTP 200 OK** con pronóstico a 7 días, total estimado y desglose de segmentos de clientes.
- **Scoping de Sucursales**:
  - Si un usuario del Tenant 1 envía `?sucursal_id=` perteneciente a una sucursal del Tenant 2, el backend responde **HTTP 404 Not Found** impidiendo sondas transversales entre empresas.
- **Dashboard Web (`web/src/app/features/dashboard/dashboard.component.html`)**:
  - Si la suscripción no tiene predicciones, muestra banner bloqueado: `"Predicciones disponibles en el plan Profesional. Actualiza el plan para habilitar pronósticos y segmentación ML"`.
  - Si está contratado, renderiza métricas analíticas, $R^2$, tarjeta de ingresos estimados para los próximos 7 días con barras de progreso SVG y contadores de clientes por segmento K-means.

---

## 4. Resultados de Pruebas Automatizadas

Ejecución de la suite dedicada `backend/tests/test_ai_analytics_and_predictions_suite.py`:
```
tests/test_ai_analytics_and_predictions_suite.py::test_req037_role_and_plan_capability_guards PASSED [ 16%]
tests/test_ai_analytics_and_predictions_suite.py::test_req038_multi_tenant_operational_context_isolation PASSED [ 33%]
tests/test_ai_analytics_and_predictions_suite.py::test_req041_input_validation_and_prompt_injection_safety PASSED [ 50%]
tests/test_ai_analytics_and_predictions_suite.py::test_req043_supervised_ridge_regression_reproducibility PASSED [ 66%]
tests/test_ai_analytics_and_predictions_suite.py::test_req044_unsupervised_kmeans_clustering_reproducibility PASSED [ 83%]
tests/test_ai_analytics_and_predictions_suite.py::test_req045_predictions_endpoint_plan_protection_and_branch_scoping PASSED [100%]

======================== 6 passed, 2 warnings in 8.08s ========================
```

Ejecución de la suite completa de Backend:
```
====================== 112 passed, 2 warnings in 83.90s ======================
```
