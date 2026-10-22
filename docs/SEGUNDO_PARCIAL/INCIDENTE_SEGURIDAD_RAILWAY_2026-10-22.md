# Respuesta al incidente de variables de Railway — 22/10/2026

## Fuente y alcance

Railway comunicó acceso potencial no autorizado a variables de entorno y recomendó rotar inmediatamente todas las variables secretas, credenciales de bases de datos y llaves de proveedores, además de revisar registros.

El servicio `StyleStore_Backend` tenía nueve variables de servicio. Las únicas credenciales configuradas eran:

- `DATABASE_URL`, definida correctamente como referencia `${{Postgres.DATABASE_URL}}`.
- `SECRET_KEY`, usada para firmar JWT.

No estaban configuradas en Railway credenciales de PayPal, SMTP, Groq ni una llave maestra global. Las demás variables eran configuración no secreta (`ALGORITHM`, duraciones, CORS, URL frontend, host y modo debug).

## Comprobaciones realizadas

- Se revisaron los registros conjuntos de backend y PostgreSQL de las últimas 24 horas.
- La búsqueda `authentication failed` no devolvió eventos.
- No se observó evidencia directa de uso indebido en los registros disponibles.
- Se detectó un problema funcional no relacionado con el incidente: la base desplegada no tiene todavía la columna `orden_venta.client_operation_uuid`, señal de que las migraciones pendientes no se ejecutaron.

La ausencia de eventos sospechosos no demuestra que una credencial no haya sido leída; por eso la rotación sigue siendo obligatoria.

## Endurecimiento incorporado al código

- Se eliminó la llave maestra global predeterminada.
- Una llave maestra vacía ya no permite desbloquear la bitácora.
- Se eliminó la contraseña inicial conocida del administrador.
- La cuenta inicial solo se crea si el operador proporciona `INITIAL_ADMIN_EMAIL` e `INITIAL_ADMIN_PASSWORD` explícitamente.
- En Railway, el backend falla de forma segura si `SECRET_KEY` falta o tiene menos de 32 caracteres.
- `.env.example` documenta las variables sin contener valores reales.

## Rotación operativa

1. Sustituir `SECRET_KEY` por un valor aleatorio nuevo de alta entropía. Esto invalida todos los JWT emitidos anteriormente.
2. En PostgreSQL, usar **Database → Config → Connection → Regenerate**. No editar `POSTGRES_PASSWORD`, `PGPASSWORD` ni ejecutar `ALTER USER` manualmente.
3. Confirmar que el backend sigue usando `${{Postgres.DATABASE_URL}}`.
4. Volver a desplegar PostgreSQL y todos los servicios consumidores cuando Railway habilite builds.
5. Ejecutar `alembic upgrade head` hasta la cabeza vigente antes de validar la aplicación.
6. Revisar logs de despliegue, errores `password authentication failed`, roles/extensiones inesperados y sesiones activas.

## Pendiente externo

- Se generó una `SECRET_KEY` nueva de 384 bits y se guardó en la configuración de Railway. El cambio no está activo todavía porque Railway mantiene los despliegues pausados; el deployment activo sigue siendo el anterior.
- GitHub continúa conectado a `dylandeam/StyleStore_Backend`, rama `main`, con auto-deploy habilitado.
- La interfaz de configuración de PostgreSQL no cargó el control `Regenerate` mientras Railway mostraba `Platform Outage`.
- La rotación de PostgreSQL debe completarse tan pronto como `Regenerate` y los redeploys estén disponibles. No se editó manualmente `POSTGRES_PASSWORD`, evitando desincronizar la base y sus variables.
- Tras reanudarse el servicio se debe desplegar backend `5dd87e8` o posterior; el comando de inicio ya ejecuta `alembic upgrade head` antes de Uvicorn.
