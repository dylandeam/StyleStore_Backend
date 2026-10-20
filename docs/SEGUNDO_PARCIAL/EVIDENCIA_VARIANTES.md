# Evidencia — Precio y medidas por variante

Fecha de comprobación: 20 de octubre de 2026.

## Implementación

- Migración aditiva `a7d1e5f903b2` sobre `stock_inventario`.
- `precio_variante` opcional por combinación de producto, color, talla y sucursal.
- `medidas` validadas en centímetros como objeto extensible, con límite de claves y rango permitido.
- Si no existe precio propio se conserva el precio base del producto para retrocompatibilidad.
- Inventario administrativo web permite editar cantidad, precio y pecho/cintura/cadera/largo/manga.
- Catálogo web y Flutter muestran precio y medidas de la selección actual.
- Carrito, venta POS y venta offline sincronizada utilizan el precio autoritativo de la variante.

## Verificación ejecutada

- `pytest -q`: **66 pruebas aprobadas**.
- Prueba vertical: ajuste de variante → catálogo → carrito con precio `279.90` y medidas.
- `alembic heads`: una sola cabeza, `a7d1e5f903b2`.
- `npx ng build --configuration production`: aprobado.
- `flutter analyze`: aprobado sin incidencias.

## Pendiente para cierre formal

- Aplicar la migración en Railway mediante el pipeline después del push.
- Captura E2E en web y dispositivo Android contra el backend desplegado.
