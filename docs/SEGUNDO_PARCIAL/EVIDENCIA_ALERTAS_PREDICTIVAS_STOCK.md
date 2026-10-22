# Evidencia de Alertas Predictivas de Agotamiento de Stock y Exportación (REQ-068)

## 1. Alcance y Propuesta de Valor
- **REQ-068 (Funcionalidad propuesta por el equipo)**: Sistema de alerta temprana y analítica predictiva de quiebre de stock por variante de prenda y sucursal, con estimación de días de cobertura, cálculo de velocidad de venta y recomendación automática de reposición, complementado con exportación a Excel y PDF.
- **Aislamiento Multi-tenant Estricto**: Cada consulta y proyección se circunscribe únicamente al inventario y ventas históricas del tenant (`empresa_id`) autenticado.
- **Modelo de Estimación Dinámica**:
  - `velocidad_diaria`: Promedio diario de unidades vendidas en la ventana histórica (por defecto 30 días) calculada desde `DetalleVenta` y `OrdenVenta`.
  - `dias_cobertura`: Días de existencias restantes calculados como `stock_actual / velocidad_diaria`.
  - **Niveles de Criticidad**:
    - `CRITICO`: Stock en 0 o cobertura estimada ≤ 3.0 días.
    - `ALTO`: Cobertura estimada entre 3.1 y 7.0 días.
    - `MEDIO`: Cobertura estimada entre 7.1 y 15.0 días o stock actual ≤ 3 unidades con demanda activa.
    - `NORMAL`: Cobertura > 15 días o sin riesgo inmediato.
  - **Reposición Sugerida**: Proyección de demanda para 30 días (`velocidad_diaria * 30 - stock_actual`), garantizando un stock de seguridad mínimo de 10 unidades.

## 2. Componentes Implementados

### Backend
1. **Lógica de Predicción (`app/services/ml_service.py`)**:
   - Método `predictive_stock_alerts(sucursal_id, criticidad, dias_horizonte)` en `MLService`.
   - Consulta correlacionada entre `StockInventario`, `ProductoColor`, `Producto`, `Talla`, `Color`, `Sucursal` y ventas efectivas en `DetalleVenta`.
2. **Endpoints API (`app/api/v1/reportes.py`)**:
   - `GET /api/v1/reportes/alertas-stock-predictivo`: Retorna KPIs agregados (evaluados, críticos, altos, medios) y lista de alertas detalladas.
   - `GET /api/v1/reportes/alertas-stock-predictivo/excel`: Genera reporte descargable en formato Excel (.xlsx con openpyxl).
   - `GET /api/v1/reportes/alertas-stock-predictivo/pdf`: Genera reporte formal imprimible en formato PDF (con reportlab).
3. **Pruebas Automatizadas (`tests/test_alertas_stock_predictivo_req068.py`)**:
   - `test_alertas_stock_predictivo_calculo_y_aislamiento`: Valida cálculo de velocidad, cobertura, criticidad y aislamiento entre Tenant 1 y Tenant 2.
   - `test_alertas_stock_predictivo_exportaciones`: Valida generación y descarga de Excel y PDF.

### Frontend Web (`web/`)
1. **Servicio (`src/app/core/services/reportes.service.ts`)**:
   - `getAlertasStockPredictivo(filters)`
   - `exportarAlertasStockExcel(filters)`
   - `exportarAlertasStockPDF(filters)`
2. **Componente de Reportes (`src/app/features/admin/reportes/`)**:
   - Sección interactiva en [reportes.component.html](file:///d:/Descargas/Proyecto%20Examen%20StyleStore/web/src/app/features/admin/reportes/reportes.component.html).
   - Filtros dinámicos por sucursal y criticidad.
   - 4 tarjetas resumen de KPIs (Prendas evaluadas, Críticos ≤3d, Riesgo Alto ≤7d, Riesgo Medio ≤15d).
   - Tabla estilizada con badges de criticidad, días restantes, velocidad diaria y unidades sugeridas para reposición.
   - Botones de exportación directa a Excel y PDF.

## 3. Resultados de Pruebas y Compilación
- **Backend**: 103 pruebas aprobadas en Pytest (100% pasando).
- **Web**: Build de producción `ng build` completado exitosamente sin errores de compilación ni de tipado.
