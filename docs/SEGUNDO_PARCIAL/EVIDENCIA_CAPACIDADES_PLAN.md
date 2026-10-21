# Evidencia — capacidades y vigencia de planes

## Reglas verificadas

- Básico conserva como mínimos productos, ventas, reservas, offline y reportes; máximo 2 sucursales, sin chatbot y sin predicciones.
- Intermedio conserva esas cinco capacidades; máximo 5 sucursales, chatbot habilitado y predicciones deshabilitadas.
- Profesional conserva esas cinco capacidades; mínimo 10 sucursales configurables hacia arriba, chatbot y predicciones habilitados.
- Solo un administrador de tenant puede solicitar el cambio de su empresa; el administrador maestro también puede asignarlo desde la consola SaaS.
- Un cliente común no puede modificar la suscripción de todo el tenant.
- Un contrato inactivo, futuro o vencido no habilita operaciones.
- Al vencer, la contratación cambia a `vencida` y el tenant queda inactivo con causa `subscription_expired`.
- Solo el administrador del tenant conserva acceso a perfil y planes para renovar.
- La renovación requiere pago confirmado y referencia auditable; al registrarse, reactiva el tenant salvo que exista una suspensión manual.

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
- Prueba específica: intenta habilitar chatbot/predicciones en Básico y comprueba su rechazo; asigna Intermedio, verifica chatbot habilitado y predicciones deshabilitadas; vence el contrato y recupera el bloqueo.
- La matriz visual presenta bloqueadas las reglas oficiales de Básico/Intermedio/Profesional y permite configurar precios, beneficios, apariencia y un cupo Profesional igual o superior a 10.
- La prueba de vigencia comprueba el ciclo completo: vencimiento, inactivación, bloqueo general, rechazo sin pago, renovación pagada y reactivación.
