# Matriz de aclaraciones SaaS — 21/10/2026

Fuente complementaria: `REQUISITOS_NUEVAS_FUNCIONALIDADES_SAAS.md`. Esta matriz no marca requisitos como terminados; contrasta el documento con evidencia del código actual y orienta el orden de implementación.

## Conflictos que requieren definición

| Tema | Plan maestro / producción actual | Nueva aclaración | Recomendación técnica |
|---|---|---|---|
| Tres planes | Antes: `basico`, `profesional`, `personalizado` | Básico, Intermedio y Profesional | Resuelto: la fila/código Personalizado se migra a Intermedio, con límite 5, chatbot sí y predicciones no, preservando IDs, contratos e historial. |
| Cambio por prenda más barata | No existe saldo definido | El documento deja la regla explícitamente pendiente | Definir antes de programar si corresponde devolución, saldo a favor o vale. No inventar una política monetaria. |

## Resultado de auditoría

| Área aclarada | Estado comprobado | Brecha concreta |
|---|---|---|
| Capacidades y límites de planes | En pruebas | Backend protege Básico/Intermedio/Profesional, vigencia, pago y sucursales; Web/Mobile reflejan chatbot y predicciones. Falta E2E desplegado. |
| Vencimiento y renovación pagada | En pruebas | El backend inactiva automáticamente el tenant vencido, conserva acceso mínimo al administrador y solo reactiva tras una captura PayPal `COMPLETED`; Web/Mobile usan el checkout real y falta E2E desplegado. |
| Administración SaaS y tenants | Parcial avanzado | Consola maestra, suspensión, administrador y suscripción existen; falta reporte maestro operativo completo por tenant/sucursal. |
| Roles y sucursales asignadas | En pruebas | RBAC y ámbito tenant se conservan; cada empleado mantiene una sucursal principal compatible y puede tener varias asignaciones horarias del mismo tenant. Falta E2E desplegado. |
| Jornadas de empleados | En pruebas | Jornada medio tiempo/tiempo completo, días y tramos horarios por sucursal implementados en API y gestión Web; falta E2E desplegado. |
| Registro de clientes | En pruebas | Selector público y asociación de una identidad cliente con varios tenants implementados en Web/Mobile, incluido cambio de tenant activo; falta E2E desplegado. |
| Medidas y precios por talla | En pruebas | Precio y medidas por variante talla/color/sucursal implementados; falta evidencia E2E desplegada. |
| Traspasos entre sucursales | En pruebas | Entidad, API y UI web implementadas con aislamiento tenant, estados, clave idempotente, bloqueo de filas, movimiento atómico y bitácora. Falta E2E desplegado. |
| Promociones agrupadas | Implementado/en pruebas | Reglas por categoría o temporada, vigencia y mayor porcentaje aislados por tenant; falta evidencia E2E desplegada. |
| Códigos de descuento | Implementado/en pruebas | Códigos por tenant/canal con vigencia y usos, aplicados en Web, POS y Mobile; falta evidencia E2E desplegada. |
| Inventario global y por sucursal | Implementado/en pruebas | Ambos niveles existen y están aislados; el flujo de traspasos está implementado y pendiente de evidencia E2E desplegada. |
| Proveedores y compras | Parcial avanzado | Compra actualiza stock; debe mantenerse la auditoría tenant en nuevas pruebas E2E. |
| Cambios y devoluciones | Implementado/en pruebas | Plazo configurable por tenant, nueva nota de venta, diferencia monetaria, saldo a favor y sucursal elegible implementados; falta evidencia E2E desplegada. |
| Reservas por bloques | En pruebas | API, reservas y recojos web/móvil comparten bloques de una hora; un índice único parcial impide ocupar concurrentemente el mismo bloque. Falta evidencia E2E desplegada. |
| Venta presencial | Implementado/en pruebas | POS busca clientes del tenant por CI/código/nombre y, si no existe cuenta, exige nombre y CI guardados en orden y recibo sin asociar la venta a otro cliente. Falta evidencia E2E desplegada. |
| Envío o recojo | Implementado/en pruebas | Web y Mobile permiten delivery o recojo; el recojo comparte agenda y exclusión de bloques con reservas. Falta evidencia E2E desplegada. |
| Productos guardados | Implementado/en pruebas | Lista única por usuario, tenant y producto, integrada con catálogo Web/Mobile; falta evidencia E2E con backend desplegado. |
| Pago y tenant | Implementado/en pruebas | Pago pertenece obligatoriamente al tenant y la confirmación emite recibo, notificación y correo idempotentes; falta evidencia E2E desplegada. |
| Calificaciones y reclamos | Implementado/en pruebas | La nota poscompra se conserva independientemente del reclamo; existen notificación con acceso, formularios Web/Mobile y seguimiento por estados aislado por tenant. Falta evidencia E2E desplegada. |

## Dependencias actualizadas

1. Validar en despliegue el flujo de traspasos ya implementado y conservarlo como dependencia cerrada técnicamente.
2. Implementar agenda de bloques de una hora compartida por reservas y recojo.
3. Extender empleados a jornadas y múltiples asignaciones de sucursal.
4. Extender cliente a membresías multi-tenant y selector público de empresa.
5. Completar promociones agrupadas y códigos de descuento.
6. Completar cambios con nota/diferencias monetarias tras definir el caso de menor precio.
7. Validar favoritos en despliegue; luego implementar calificaciones/reclamos y notificaciones poscompra.

## Reglas transversales incorporadas

- Toda nueva tabla operativa llevará `empresa_id` e índices de ámbito cuando corresponda.
- El tenant efectivo se derivará del usuario/sesión, nunca de un ID confiado al cliente.
- Los movimientos de stock serán atómicos e idempotentes cuando puedan reintentarse.
- Las migraciones serán aditivas y preservarán filas y contratos existentes.
- Web y Mobile se actualizarán cuando el contrato API afecte a clientes o personal operativo.
