# Contrato de sincronización offline v1

## Alcance

`POST /api/v1/sync/operations` acepta reservas y ventas presenciales de contado generadas por la PWA o Flutter. El servidor siempre deriva empresa y usuario del JWT; nunca confía en un tenant enviado dentro del payload.

Cada operación lleva un UUID permanente. Repetir el mismo UUID devuelve el resultado registrado y no crea otra reserva, venta ni descuento de stock. También existe envío de hasta 50 elementos mediante `POST /api/v1/sync/batch` y consulta del historial propio con `GET /api/v1/sync/operations`.

## Solicitud v1

```json
{
  "operation_uuid": "7db30ba8-39a2-4de7-86bb-a64e68a5b263",
  "operation_type": "reserva",
  "payload_version": 1,
  "client_created_at": "2026-10-20T10:00:00-04:00",
  "payload": {
    "sucursal_id": 4,
    "fecha_limite": "2026-10-22",
    "hora_retiro": "15:30:00",
    "items": [{ "stock_inventario_id": 91, "cantidad": 1 }]
  }
}
```

Tipos admitidos:

- `reserva`: aplica elegibilidad, máximo de tres días, horario de la sucursal y bloqueo de stock.
- `venta_efectivo`: aplica permisos de caja, pertenencia tenant y bloqueo de stock. QR, PayPal y cualquier pago electrónico offline se rechazan.

## Estados y resolución

| Estado | Significado | Acción del cliente |
|---|---|---|
| `procesando` | El servidor aceptó el UUID y aún ejecuta la validación | Mantener local y consultar/reintentar con el mismo UUID |
| `confirmada` | Existe reserva/venta central y `result_id` identifica el recurso | Mostrar confirmación definitiva |
| `rechazada` | Permiso, contrato o medio de pago no válido | Conservar historial y mostrar `reason` |
| `conflicto` | Horario, sucursal o stock central ya no permite la operación | Informar “Prenda no disponible” o el motivo exacto y ofrecer corregirla |

Una caída de red mantiene el registro local como pendiente. Nunca se elimina en un intento fallido. La PWA reenvía al recuperar conectividad y el índice único del UUID protege contra respuestas perdidas o reintentos simultáneos.
