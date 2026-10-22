# Evidencia de Diagnóstico Sync y Resolución de Conflictos de Stock (REQ-066, REQ-070)

Fecha: 22/10/2026.  
Ámbito: Backend (FastAPI) y Web PWA (Angular 21).  
Requisitos cubiertos: `REQ-066` y `REQ-070`.

---

## 1. Mensaje Uniforme de "Prenda no disponible" (REQ-066)

Se unificó el mensaje de error ante insuficiencia o competencia concurrente por la última existencia física de un producto en todos los canales de venta:
- **Venta Presencial POS (`app/api/v1/ventas.py`):**
  - Si el stock es inferior a lo solicitado:
    `"Prenda no disponible: Stock insuficiente en sucursal. Disponible: {disponible}, solicitado: {solicitado}. Por favor revisa otras variantes o sucursales."`
- **Reservas de Prendas (`app/api/v1/reservas.py`):**
  - Si la última unidad fue reservada o tomada concurrentemente:
    `"Prenda no disponible: Stock insuficiente para el ítem {stock_id}. Disponible: {disponible}, solicitado: {solicitado}. Por favor revisa otras variantes o sucursales."`
- **Carrito y Checkout Online (`app/api/v1/carrito.py`):**
  - Si otra transacción en línea tomó las unidades durante el checkout:
    `"Prenda no disponible: Stock insuficiente para '{prod_name}'. Requerido: {item.cantidad}, Disponible: {stock.cantidad}. Por favor revisa otras variantes o sucursales."`

---

## 2. Métricas Agregadas y Diagnóstico de Sincronización Offline (REQ-070)

Se implementó el endpoint `GET /api/v1/sync/metricas`:
- **Aislamiento Multi-tenant:** El endpoint extrae el `empresa_id` del usuario autenticado; usuarios de una empresa solo visualizan sus métricas y el administrador SaaS puede supervisar métricas consolidadas o por tenant.
- **Filtro Opcional:** Permite filtrar por `sucursal_id`.
- **Métricas Retornadas (`SyncMetricasResponse`):**
  - `total_operaciones`: Conteo histórico de operaciones offline procesadas.
  - `total_confirmadas`: Operaciones exitosas que impactaron inventario y crearon órdenes.
  - `total_conflictos`: Operaciones que detectaron inconsistencia o agotamiento de existencias y dispararon reembolsos.
  - `total_rechazadas`: Operaciones que no cumplieron con validaciones de negocio.
  - `tasa_exito_porcentaje`: Indicador de fiabilidad del proceso de sincronización.
  - `operaciones_por_tipo`: Desglose cuantitativo (`venta_efectivo`, `reserva`).
  - `reembolsos_asociados`: Total de reembolsos generados, monto acumulado, pendientes y entregados.
  - `conflictos_recientes`: Lista estructurada de los últimos 10 incidentes con UUID, timestamp, motivo de rechazo y enlace al reembolso sin exponer PII sensible.

---

## 3. Pruebas Automatizadas Reproducibles

Se añadieron pruebas específicas en `backend/tests/test_sync_metricas_conflicto.py`:
1. `test_uniform_prenda_no_disponible_message`: Verifica que una venta presencial con stock 0 retorne `HTTP 400` con el mensaje explícito `"Prenda no disponible"`.
2. `test_sync_metrics_and_diagnostics_aggregation`: Simula una operación exitosa y una en conflicto, consultando `GET /sync/metricas` y validando cálculos de tasa de éxito, conteo de reembolsos y el ítem de diagnóstico estructurado.

**Comando de verificación:**
```powershell
pytest -q tests/test_sync_metricas_conflicto.py
```
**Resultado:** `2 passed in 3.05s`.

Suite completa de backend: **99 passed, 2 warnings** en 69.40s.
Compilación de Angular Web: `main-G7I2NEIM.js` sin errores.
