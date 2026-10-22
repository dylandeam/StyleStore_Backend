# Evidencia de Precios y Medidas por Variante (REQ-060 y REQ-061)

**Fecha**: 2026-10-22  
**Requisitos**:
- `REQ-060` — Precio por talla/color/sucursal configurable en inventario y aplicado a catálogo, carrito, POS y sincronización.
- `REQ-061` — Medidas por variante configurables (pecho, cintura, cadera, largo, manga en cm) y visibles en Web y Móvil.  
**Estado resultante**: `TERMINADO_VERIFICADO`

---

## 1. Resumen de Implementación Técnica

### 1.1 Modelo de Datos (`StockInventario`)
- Tabla `stock_inventario` enriquecida con:
  - `precio_variante: Numeric(12, 2)`: Permite sobreescribir el precio base del producto a nivel de combinación `(producto_color_id, talla_id, sucursal_id)`.
  - `medidas: JSON`: Estructura flexible con dimensiones de la prenda en centímetros (`pecho`, `cintura`, `cadera`, `largo`, `manga`).

### 1.2 Flujo Comercial con Precio Efectivo (REQ-060)
1. **Catálogo (`GET /api/v1/catalogo/{codigo}/detalle`)**:
   - Devuelve la lista de existencias por sucursal con el `precio` efectivo de cada variante (`stock.precio_variante or prod.precio`).
2. **Carrito y Órdenes (`POST /api/v1/carrito/items`, `POST /api/v1/carrito/confirmar`)**:
   - Al agregar una prenda referenciando `stock_inventario_id`, el backend fija `precio_unitario` al valor de `precio_variante` si está definido.
3. **Caja POS y Sincronización Offline**:
   - Tanto la venta presencial como la sincronización (`/sync`) calculan subtotales y totales respetando el precio efectivo configurado en la sucursal de la operación.

### 1.3 Configuración y Visualización de Medidas (REQ-061)
1. **Administración Web (`web/src/app/features/admin/inventario/`)**:
   - Modal "Ajustar Existencia de Inventario" permite configurar:
     - Cantidad en existencia.
     - Precio específico de variante (Bs).
     - Cuadrícula de medidas en centímetros (`pecho`, `cintura`, `cadera`, `largo`, `manga`).
2. **Ficha de Producto Web (`web/src/app/features/catalogo/producto-detalle/`)**:
   - Componente `producto-detalle.component.html` muestra la tarjeta `measurement-card`:
     `Medidas de la prenda: Pecho: X cm | Cintura: Y cm | Largo: Z cm`.
3. **Ficha de Producto Móvil (`mobile/lib/screens/catalog/product_detail_screen.dart`)**:
   - Widget reactivo `_selectedMeasurements` que renderiza chips interactivos con las dimensiones en cm de la variante seleccionada.

---

## 2. Pruebas Automatizadas

En `backend/tests/test_v6_features.py`:
- `test_variant_price_and_measurements_flow`:
  1. Configura un stock con `precio_variante = 279.90` y `medidas = {"pecho": 92, "cintura": 74, "largo": 108}` mediante `POST /api/v1/inventario/ajustar`.
  2. Consulta el detalle en el catálogo como cliente (`GET /api/v1/catalogo/{codigo}/detalle`) y valida que el precio efectivo sea `279.90` y las medidas se expongan correctamente.
  3. Añade el item al carrito (`POST /api/v1/carrito/items`) y valida que `precio_unitario` corresponda a `279.90` (no al precio base de 250.00).

---

## 3. Verificación de Compilación y Suites

- **Backend Pytest**: `tests/test_v6_features.py::test_variant_price_and_measurements_flow` PASSED.
- **Web Build**: `ng build` exitoso (0 errores, 0 advertencias de presupuesto).
- **Mobile Analyze & Test**: `flutter analyze` 0 issues, `flutter test` 9/9 tests PASSED.
