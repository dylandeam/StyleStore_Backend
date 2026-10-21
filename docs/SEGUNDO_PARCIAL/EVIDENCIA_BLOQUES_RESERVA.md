# Evidencia parcial REQ-059 — Bloques horarios de reserva

Fecha: 2026-10-21

## Implementado

- Endpoint `GET /api/v1/reservas/disponibilidad?sucursal_id=...&fecha=...`.
- Generación de bloques completos de una hora dentro del horario configurable de cada sucursal.
- Bloques pasados y bloques pendientes ya ocupados se devuelven como no disponibles.
- Solo se aceptan horas de inicio presentes en los bloques generados.
- Índice único parcial `uq_reserva_bloque_activo` sobre sucursal, fecha y hora para reservas pendientes.
- La colisión concurrente se revierte y devuelve un mensaje claro sin descontar stock.
- Selectores web y móvil consumen la disponibilidad y muestran horarios ocupados deshabilitados.
- El checkout web permite elegir delivery o recojo, guarda fecha/hora en la orden y ocupa el mismo calendario mediante una cita `recojo_compra`.

## Verificación

- Suite backend: `71 passed`.
- Build Angular: correcto.
- `flutter analyze`: sin problemas.
- Alembic: una sola cabeza `f2c8d9e0a711`; SQL offline PostgreSQL generado correctamente.

## Pendiente

Falta incorporar el selector de recojo al checkout móvil (actualmente solo presenta delivery) y ejecutar evidencia E2E desplegada.
