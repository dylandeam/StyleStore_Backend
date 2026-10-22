# Evidencia de Agenda Compartida para Reservas y Recojos (REQ-059)

**Fecha**: 2026-10-22  
**Requisito**: `REQ-059` — Agenda compartida implementada para reservas de prendas y recojo de compras web/móvil, con bloques horarios de una hora, ventana máxima de 3 días y exclusión concurrente en base de datos.  
**Estado resultante**: `TERMINADO_VERIFICADO`

---

## 1. Diseño Arquitectónico y Reglas de Negocio

1. **Definición de Horario y Bloques (`app/services/agenda_service.py`)**:
   - Generación determinística de bloques de 1 hora (`hour_blocks`) dentro del horario de apertura y cierre de la sucursal (`hora_apertura`, `hora_cierre`).
   - Los bloques deben estar entre hoy y un máximo de 3 días en adelante (`hoy + timedelta(days=3)`).
   - Los bloques pasados respecto a la hora del día actual se marcan como no disponibles automáticamente.

2. **Exclusión Concurrente Única (`uq_reserva_bloque_activo`)**:
   - La tabla `reservas` cuenta con la restricción de unicidad para citas activas:
     `uq_reserva_bloque_activo` que cubre `(sucursal_id, fecha, hora)` para estados pendientes.
   - Tanto una **reserva presencial de prendas** como una cita de **recojo de compra en tienda** (`tipo == "recojo_compra"`, originada desde el checkout online) crean una fila en `reservas`.
   - Si dos usuarios compiten concurrentemente por el mismo bloque horario en la misma sucursal, la base de datos aborta la transacción competidora con `IntegrityError` y la API retorna HTTP 400 informando: `"El bloque de recojo acaba de ser ocupado. Selecciona otro horario disponible."`

3. **Consulta de Disponibilidad (`GET /api/v1/reservas/disponibilidad`)**:
   - Endpoint público autenticado que recibe `sucursal_id` y `fecha`.
   - Retorna la lista de bloques horarios (`inicio`, `fin`) y la bandera booleana `disponible` reflejando de forma unificada tanto reservas de probador como recojos de compras ya agendados.

---

## 2. Consumo en Frontend Web y Móvil

1. **Web (`web/src/app/`)**:
   - Ficha de Producto (`features/catalogo/producto-detalle/`): Al pulsar "Reservar Prenda", consulta `getDisponibilidad(sucursalId, fecha)` y deshabilita los bloques ya ocupados.
   - Carrito y Checkout (`features/carrito/`): Al elegir "Recoger en tienda", carga la disponibilidad de la sucursal y bloquea las horas ocupadas antes de confirmar la compra.
2. **Mobile (`mobile/lib/`)**:
   - Detalle de Prenda (`screens/catalog/product_detail_screen.dart`): Calendario de reserva limitado a 3 días y consulta de disponibilidad horaria mediante `ApiConfig.reservasDisponibilidadUrl`.
   - Checkout con Recojo (`screens/cart/` / `catalog_screen.dart`): Envío de `tipo_entrega: "recojo"`, `fecha_recojo` y `hora_recojo` a `/carrito/checkout`.

---

## 3. Pruebas Automatizadas

En `backend/tests/test_v6_features.py`:
1. `test_checkout_recojo_ocupa_agenda_compartida`:
   - Confirma una orden de compra con `tipo_entrega="recojo"`, `fecha_recojo=mañana` y `hora_recojo=10:00`.
   - Inmediatamente consulta `GET /api/v1/reservas/disponibilidad` para esa sucursal y fecha.
   - Comprueba que el bloque `"10:00"` queda marcado como `disponible: False`.
2. `test_checkout_integral_movil_programa_recojo`:
   - Valida el endpoint móvil integral `/carrito/checkout` agendando cita de recojo compartida.
3. `test_reserva_respeta_horario_y_maximo_tres_dias`:
   - Verifica el cumplimiento del horario de la sucursal y el límite máximo estricto de 3 días.

---

## 4. Estado de Validación

- Backend: **106 tests pasados**, 0 errores.
- Web: `ng build` exitoso sin advertencias.
- Mobile: `flutter analyze` 0 issues, `flutter test` 9 pasados.
