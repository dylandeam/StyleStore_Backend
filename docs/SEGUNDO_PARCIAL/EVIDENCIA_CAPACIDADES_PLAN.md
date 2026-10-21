# Evidencia — capacidades y vigencia de planes

## Reglas verificadas

- Básico conserva como mínimos: productos, ventas, reservas, offline y reportes; máximo 2 sucursales y sin IA generativa.
- Profesional conserva esas cinco capacidades; máximo 10 sucursales e IA generativa habilitada.
- Personalizado permite configurar manualmente cupo y capacidades desde administración.
- Solo un administrador de tenant puede solicitar el cambio de su empresa; el administrador maestro también puede asignarlo desde la consola SaaS.
- Un cliente común no puede modificar la suscripción de todo el tenant.
- Un contrato inactivo, futuro o vencido no habilita operaciones.

## Operaciones protegidas en backend

- Escritura de productos, inventario y compras a proveedores.
- Generación de ventas, checkout y cobros.
- Creación de reservas, conservando consulta y cancelación histórica.
- Envío de operaciones de sincronización offline.
- Reportes convencionales y, adicionalmente, control específico de IA generativa.

La lectura histórica no se bloquea al vencer el plan, para permitir auditoría, recuperación y cancelaciones seguras sin crear nuevas operaciones comerciales.

## Verificación — 21/10/2026

- Suite backend completa: **68 pruebas aprobadas**.
- Web: **2 pruebas aprobadas** y compilación de producción correcta.
- Prueba específica: intenta desactivar mínimos de Básico, comprueba su restauración; asigna Personalizado vacío y obtiene 403 en reportes/offline; habilita la capacidad y obtiene acceso; vence el contrato y recupera el bloqueo.
- La matriz visual del administrador permite editar las capacidades del plan Personalizado y presenta bloqueados los mínimos oficiales de Básico/Profesional.
