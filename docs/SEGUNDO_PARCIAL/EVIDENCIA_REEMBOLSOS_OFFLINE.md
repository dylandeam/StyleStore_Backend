# Evidencia — reembolsos por conflicto offline

## Regla aplicada

Una `venta_efectivo` cobrada localmente que el servidor rechaza por stock o disponibilidad genera un reembolso `pendiente`. El importe procede de la instantánea inmutable enviada con la operación. QR y pagos electrónicos no participan del flujo offline.

El reembolso conserva `operation_uuid`, operación de sincronización, tenant, usuario, sucursal, monto, motivo y fechas. La unicidad de operación impide duplicarlo durante replay. Una vez `entregado` o `cancelado`, no puede volver a resolverse.

## Superficies

- API: `GET /reembolsos/mios`, `GET /reembolsos` y `PUT /reembolsos/{id}`.
- Web staff: `/admin/reembolsos`, filtrado por estado, registro de entrega/cancelación y observación obligatoria.
- Cola PWA: muestra identificador, estado e importe del reembolso devuelto por sync.
- Cola Flutter: incorpora el reembolso pendiente al resultado visible de la operación.
- Seguridad: el usuario solo consulta sus propios reembolsos; staff opera únicamente dentro de su tenant y el maestro conserva alcance global.

## Verificación automatizada — 21/10/2026

- Backend completo: **67 pruebas aprobadas**.
- Prueba vertical específica: rechazo por stock → reembolso pendiente → replay sin duplicado → consulta → entrega → intento de segunda resolución rechazado.
- Web: compilación de producción aprobada.
- Flutter: análisis estático sin incidencias.
- Migración Alembic: `b8e2f6041c73_add_offline_refunds.py`, sucesora de `a7d1e5f903b2`.

El requisito permanece `EN_PRUEBAS` hasta conservar evidencia de la secuencia completa con una venta física creada sin conexión en el Samsung S21+ y sincronizada posteriormente.
