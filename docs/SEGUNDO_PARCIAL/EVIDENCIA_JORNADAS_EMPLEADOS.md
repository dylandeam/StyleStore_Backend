# Evidencia técnica — jornadas y asignaciones de empleados

Fecha: 2026-10-21

## Alcance implementado

- Jornada global `tiempo_completo` o `medio_tiempo` por empleado.
- Una o varias asignaciones de sucursal por empleado, preservando `sucursal_id` como sucursal principal para compatibilidad.
- Hora inicial, hora final y días laborables independientes por sucursal.
- La sucursal y el `empresa_id` efectivo se validan en servidor a partir del tenant autenticado.
- Una sucursal de otro tenant devuelve 404 y no modifica las asignaciones existentes.
- La hora inicial debe ser anterior a la final, no se admiten sucursales repetidas y se exige al menos una asignación.
- Los clientes API antiguos que solo envían `sucursal_id` reciben automáticamente una asignación con el horario configurado de esa sucursal.

## Persistencia y migración

- Nueva tabla `empleado_sucursales`, con claves foráneas a empresa, empleado y sucursal.
- Restricción única por empleado+sucursal e índices de empresa, empleado y sucursal.
- Nueva columna `empleados.jornada_tipo` con restricción de valores.
- La migración `c5f7a9b1d234` crea una asignación inicial para cada empleado existente usando su sucursal principal y horario comercial.

## Interfaz Web

- El formulario permite elegir jornada, múltiples sucursales, sucursal principal, horas y días.
- La tabla muestra todas las asignaciones y sus horarios; el filtro por sucursal contempla asignaciones principales y secundarias.
- El administrador SaaS conserva acceso de supervisión sin mutaciones; cada administrador tenant gestiona únicamente su personal.

## Verificación automatizada

- Prueba vertical: alta con dos sucursales y horarios distintos, serialización de jornada/días, rechazo de sucursal ajena y rechazo de horario invertido.
- Regresión backend completa: `74 passed` (dos advertencias deprecadas de Starlette/TestClient).
- Cabeza Alembic única: `c5f7a9b1d234`; SQL PostgreSQL de esta revisión generado correctamente.
- Build Angular de producción aprobado: bundle `main-MX7NO5RY.js`.

Pendiente para cierre formal: aplicar la migración y capturar evidencia E2E cuando Railway reanude los despliegues.
