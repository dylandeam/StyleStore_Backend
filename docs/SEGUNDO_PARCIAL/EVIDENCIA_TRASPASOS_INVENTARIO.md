# Evidencia REQ-062 — Traspasos de inventario

Fecha: 2026-10-21

## Alcance implementado

- Traspasos entre dos sucursales del mismo tenant para una variante producto/color/talla.
- Estados `pendiente`, `aprobado`, `rechazado` y `cancelado`.
- Clave idempotente única por tenant para evitar solicitudes duplicadas.
- Aprobación idempotente: repetirla no vuelve a descontar existencias.
- Revalidación de stock al aprobar y bloqueo PostgreSQL de las filas involucradas en orden estable.
- Descuento de origen y alta o incremento de destino dentro de la misma transacción.
- Copia del precio y medidas de variante cuando se crea la existencia de destino.
- Registro en bitácora de solicitud y decisión.
- Aislamiento tenant sin revelar recursos de otras empresas.
- UI web integrada en Gestión de Inventario; cajero conserva solo lectura.

## API

- `GET /api/v1/inventario/traspasos`
- `POST /api/v1/inventario/traspasos`
- `POST /api/v1/inventario/traspasos/{id}/aprobar`
- `POST /api/v1/inventario/traspasos/{id}/rechazar`
- `POST /api/v1/inventario/traspasos/{id}/cancelar`

## Verificación local

- Suite backend completa: `70 passed`.
- Pruebas específicas: idempotencia, aprobación repetida, insuficiencia sobrevenida de stock y aislamiento tenant.
- Build web Angular 21: correcto.
- Alembic: una sola cabeza `e7b3c4d5a610`; SQL offline de la migración generado correctamente para PostgreSQL.

Pendiente para marcar como terminado: evidencia E2E sobre el entorno desplegado.
