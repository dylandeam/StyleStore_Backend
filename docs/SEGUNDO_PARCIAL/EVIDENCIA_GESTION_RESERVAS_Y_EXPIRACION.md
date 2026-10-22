# Evidencia de Gestión de Reservas, Búsqueda Multi-tenant y Expiración Automática (REQ-058)

## 1. Alcance y Requisitos Verificados
- **REQ-058**: Reservas cliente y staff con ciclo de vida completo (pendiente, confirmada, rechazada, entregada, vencida, cancelada), expiración automática con restitución atómica de stock inventario y búsqueda/filtrado multi-tenant.
- **Aislamiento Multi-tenant**: Cada consulta y acción de reservas se encuentra estrictamente delimitada por `empresa_id` obtenido del JWT del usuario autenticado.
- **Restitución Atómica**: Al transicionar a `vencida` o `cancelada`, las unidades reservadas se devuelven a `StockInventario` con bloqueo pesimista `with_for_update()` y se emite bitácora de auditoría.

## 2. Cambios Implementados

### Backend
1. **Modelos y Esquemas (`app/schemas/reserva.py`)**:
   - Adición del estado `vencida` en `ReservaEstadoUpdate`.
   - Adición de esquema `ExpirarReservasResponse` con conteo de reservas expiradas, ítems restituidos y detalle auditado.
2. **Endpoints y Lógica Transaccional (`app/api/v1/reservas.py`)**:
   - `GET /api/v1/reservas`: Incorporación de filtros `search` (código, cliente, CI, producto, variante), `fecha_desde`, `fecha_hasta`, y verificación periódica/en línea de reservas vencidas (`expirar_reservas_vencidas_db`).
   - `POST /api/v1/reservas/expirar-vencidas`: Endpoint explícito para staff y administradores para procesar y liberar stock vencido de forma atómica en su tenant/sucursal.
   - `PUT /api/v1/reservas/{id}/estado`: Integración de restitución de stock al cancelar o marcar como vencida una reserva activa.
3. **Pruebas Automatizadas (`tests/test_reservas_tenant_busqueda_expiracion.py`)**:
   - `test_reservas_multi_tenant_busqueda_y_filtros`: Valida aislamiento tenant, búsqueda por nombre y código, filtros por rango de fechas y estados.
   - `test_expiracion_reservas_restitucion_stock_y_auditoria`: Valida que reservas vencidas liberan el stock reservado atómicamente, pasan a estado `vencida` y registran auditoría.

### Frontend Web
1. **Servicio (`src/app/core/services/reserva.service.ts`)**:
   - Parámetros `search`, `fecha_desde`, `fecha_hasta` en `getReservas()`.
   - Método `expirarVencidas(sucursal_id?)` conectado a la API.
2. **Componente (`src/app/features/admin/reservas/`)**:
   - Campo reactivo de búsqueda en tiempo real.
   - Botón de acción para expirar reservas vencidas y liberar stock.
   - Opción de filtro por estado "Vencida".

## 3. Resultados de Pruebas y Compilación
- **Backend**: 101 pruebas aprobadas en Pytest (100% pasando).
- **Web**: Build de producción exitoso con Angular CLI sin errores de tipo ni de empaquetado (`ng build` completado exitosamente).
