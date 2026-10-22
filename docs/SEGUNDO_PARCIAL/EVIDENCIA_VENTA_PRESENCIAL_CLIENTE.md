# Evidencia — identificación del comprador en venta presencial

## Alcance cerrado

- Caja permite buscar clientes del tenant activo por CI, código, nombre o apellido.
- Seleccionar un cliente registrado vincula únicamente ese perfil; un código ajeno o inexistente devuelve 404.
- Para un comprador sin cuenta se exigen nombre y CI/documento.
- Nombre y CI se guardan como snapshot en la orden y se exponen en la venta, historial y recibo.
- Una venta de mostrador no crea una cuenta ficticia ni se asigna silenciosamente al primer cliente del tenant.
- Las colas offline antiguas con `CLI-GENERAL`/`GENERICO` siguen sincronizando con identificación de legado auditable.

## Persistencia

- Migración Alembic: `1c3d5e7f9012`.
- `orden_venta.codigo_cliente` pasa a ser opcional solo para compradores sin cuenta.
- Nuevos campos: `comprador_nombre` y `comprador_ci`, con índice de consulta por CI.

## Verificación local

- Pruebas específicas: `3 passed`.
- Regresión backend completa: `88 passed`.
- Sincronización offline: `5 passed`.
- Build Angular de producción: correcto, bundle `main-7O6HK3TZ.js`.
- Cabeza Alembic única: `1c3d5e7f9012`.

Pendiente para cierre E2E: aplicar la migración en Railway y comprobar búsqueda, venta e impresión del recibo contra el backend desplegado.
