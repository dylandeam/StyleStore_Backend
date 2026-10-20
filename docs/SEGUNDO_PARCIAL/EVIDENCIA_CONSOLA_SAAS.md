# Evidencia — Consola SaaS del administrador maestro

Fecha de comprobación: 20 de octubre de 2026.

## Alcance implementado

- La cuenta maestra se distingue mediante `is_platform_admin`; no es un rol asignable a un tenant.
- El rol RBAC `administrador` representa explícitamente al **Administrador de tenant**.
- Solo el administrador maestro puede listar el resumen global, crear y editar tenants, suspender/reactivar empresas, gestionar su administrador y asignar o renovar suscripciones.
- Cada tenant nuevo recibe un administrador propio y una contratación inicial auditable del plan elegido.
- La consola expone usuarios y sucursales consumidos, responsable, plan, estado e inicio/vencimiento.
- Suspender una empresa invalida las operaciones posteriores de sus usuarios, incluso si conservan un JWT todavía vigente.
- Las renovaciones conservan el historial marcando la contratación activa anterior como reemplazada.

## Endpoints protegidos

- `GET /api/v1/empresas/resumen`
- `GET /api/v1/empresas/{empresa_id}`
- `PATCH /api/v1/empresas/{empresa_id}`
- `PUT /api/v1/empresas/{empresa_id}/estado`
- `PUT /api/v1/empresas/{empresa_id}/administrador`
- `PUT /api/v1/empresas/{empresa_id}/suscripcion`

Todos exigen `require_platform_admin`; el tenant se obtiene desde el recurso del servidor y no desde el JWT de otro usuario ni desde un ámbito seleccionable por el cliente.

## Verificación ejecutada

- `pytest -q`: **64 pruebas aprobadas**.
- `pytest tests/test_tenant_foundation.py -q`: **10 pruebas aprobadas**.
- `npx ng build --configuration production`: compilación de producción aprobada.
- `npx ng test --watch=false`: **2 pruebas aprobadas**.
- Se verifican creación, resumen, edición, cambio de responsable/contraseña, renovación, suspensión, reactivación y rechazo de acceso desde administrador tenant.

## Pendiente para cierre formal

- Evidencia visual E2E sobre el despliegue público después del push.
- Aplicación exhaustiva de capacidades y cupos de plan en todos los módulos del dominio.
- Cierre del aislamiento de recursos secundarios indicado en el tablero de requisitos.
