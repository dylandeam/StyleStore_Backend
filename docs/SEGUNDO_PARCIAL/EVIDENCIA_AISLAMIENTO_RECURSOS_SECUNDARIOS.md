# Evidencia de aislamiento de recursos secundarios

Fecha: 21/10/2026.

## Alcance cerrado

- `uploaded_files` pertenece obligatoriamente a una empresa. Solo administrador o encargado pueden subir archivos y el nombre físico incorpora el tenant.
- Los respaldos contienen datos globales y, por ello, toda su API exige administrador SaaS global. Un administrador tenant recibe HTTP 403.
- `proximamente` pertenece a una empresa. Listado, lectura, edición, eliminación y notificación respetan el tenant; las referencias a proveedor, categoría, temporada y colección se validan dentro de la misma empresa.
- El administrador SaaS puede supervisar próximos lanzamientos de todos los tenants, con la empresa visible, pero no modificar sus datos.
- Las suscripciones de próximos lanzamientos y stock rechazan objetivos de otra empresa.
- Los trabajos de prueba virtual pertenecen al usuario y empresa activos. El acceso por ID de otro tenant devuelve HTTP 404 y las fotos aceptan únicamente JPG, PNG o WEBP de hasta 5 MB.

## Datos y migración

La revisión Alembic `2d4e6f809123` agrega y rellena `empresa_id` en archivos, próximos lanzamientos y pruebas virtuales. La cadena completa se aplicó en un esquema PostgreSQL temporal vacío: 52 tablas y una sola cabeza.

## Pruebas reproducibles

```powershell
pytest -q
npm.cmd run build
```

Resultado local: 92 pruebas backend aprobadas y bundle Angular de producción `main-EGY4FANH.js` generado correctamente.

Los casos automatizados específicos comprueban: prohibición de respaldos para administradores tenant, prohibición de uploads para clientes, asociación del archivo al tenant, aislamiento A/B de próximos lanzamientos y suscripciones, y bloqueo del IDOR de prueba virtual.

## Pendiente externo

Railway debe reanudar sus builds, desplegar el commit de esta fase y ejecutar `alembic upgrade head`. Hasta entonces, el backend público no constituye evidencia de esta revisión.
