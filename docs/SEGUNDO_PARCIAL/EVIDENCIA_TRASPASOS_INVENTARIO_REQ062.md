# Evidencia de Traspasos Seguros de Inventario entre Sucursales (REQ-062)

**Fecha**: 2026-10-22  
**Requisito**: `REQ-062` — Traspasos de inventario seguros entre sucursales de un mismo tenant con entidad propia, API dedicada, UI web, aislamiento multi-tenant, idempotencia, bloqueo y movimiento atómico de stock.  
**Estado resultante**: `TERMINADO_VERIFICADO`

---

## 1. Arquitectura y Reglas del Traspaso

1. **Entidad del Modelo (`app/models/traspaso_inventario.py`)**:
   - `TraspasoInventario` con tabla `traspasos_inventario`.
   - Restricciones de integridad a nivel PostgreSQL:
     - `uq_traspaso_empresa_idempotency`: Clave única compuesta `(empresa_id, idempotency_key)` que previene duplicados en reenvíos de red.
     - `ck_traspaso_cantidad_positiva`: Asegura que `cantidad > 0`.
     - `ck_traspaso_sucursales_distintas`: Impide traspasos donde origen y destino sean la misma sucursal.
     - `ck_traspaso_estado`: Estados válidos controlados (`pendiente`, `aprobado`, `rechazado`, `cancelado`).
   - Aislamiento tenant estricto mediante `empresa_id` con FK a `empresas.id`.

2. **Endpoints de la API (`app/api/v1/inventario.py`)**:
   - `POST /api/v1/inventario/traspasos`: Crea una solicitud de traspaso verificando pertenencia al tenant, suficiencia de stock en la sucursal de origen y retornando la entidad de traspaso de forma idempotente.
   - `GET /api/v1/inventario/traspasos`: Lista las solicitudes de traspaso del tenant autenticado con filtro opcional por estado y sucursal.
   - `POST /api/v1/inventario/traspasos/{id}/aprobar`:
     - Aplica bloqueo pesimista de fila (`with_for_update()`) en la sucursal origen.
     - Revalida en el instante de la transacción que la cantidad siga disponible.
     - Decrementa el stock en origen.
     - Incrementa o crea el registro en destino conservando el precio de variante (`precio_variante`) y las medidas (`medidas`).
     - Actualiza el estado a `aprobado` y registra la acción en la bitácora auditable.
   - `POST /api/v1/inventario/traspasos/{id}/rechazar`: Marca la solicitud como `rechazada` sin mover inventario.
   - `POST /api/v1/inventario/traspasos/{id}/cancelar`: Permite al solicitante cancelar una petición pendiente.

3. **Interfaz Web (`web/src/app/features/admin/inventario/`)**:
   - Pestaña "Traspasos" en el módulo de Inventario con listado reactivo de solicitudes, estados con badges de color, observaciones y botones de acción.
   - Botón "⇄ Traspasar" en la tabla de inventario que abre un modal con selector de sucursal destino, cantidad limitada al stock actual y campo de observación.
   - Generación de `idempotency_key` con `crypto.randomUUID()` en el cliente.

---

## 2. Cobertura de Pruebas Automatizadas

En `backend/tests/test_inventory_transfers.py`:
1. `test_transfer_is_idempotent_and_moves_stock_once`:
   - Crea un traspaso con `idempotency_key`.
   - Reenvía el mismo payload y confirma que no se duplica la orden (retorna el mismo ID).
   - Aprueba el traspaso: comprueba que el stock origen se reduce exactamente de 10 a 6 y el destino aumenta de 0 a 4.
   - Reintentar la aprobación no vuelve a mover stock (idempotencia en aprobación).
   - Confirma que el destino conserva el `precio_variante` (Bs 275) y las `medidas` (pecho: 100).
2. `test_transfer_revalidates_stock_and_is_tenant_scoped`:
   - Si el stock de origen se reduce antes de aprobar, la aprobación es rechazada con HTTP 409 Conflict y el stock no se altera.
   - Una consulta desde otro tenant autenticado devuelve lista vacía (`[]`) sin filtración cruzada.

---

## 3. Verificación de Suites y Builds

- **Backend Pytest**: `tests/test_inventory_transfers.py` aprobado (2/2 tests PASSED).
- **Web Build**: `ng build --configuration production` completado con 0 errores (`main-4SBJO6QY.js`, 1.82 MB).
- **Mobile Analyze & Test**: `flutter analyze` 0 issues, `flutter test` 9/9 tests PASSED.
