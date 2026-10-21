# Matriz de aclaraciones SaaS — 21/10/2026

Fuente complementaria: `REQUISITOS_NUEVAS_FUNCIONALIDADES_SAAS.md`. Esta matriz no marca requisitos como terminados; contrasta el documento con evidencia del código actual y orienta el orden de implementación.

## Conflictos que requieren definición

| Tema | Plan maestro / producción actual | Nueva aclaración | Recomendación técnica |
|---|---|---|---|
| Tres planes | `basico`, `profesional`, `personalizado` | Básico, Intermedio y Profesional | Mantener Básico y Profesional; migrar de forma aditiva la fila/código Personalizado a Intermedio, con límite 5, chatbot sí y predicciones no. Preservar historial y contratos por ID. |
| Cambio por prenda más barata | No existe saldo definido | El documento deja la regla explícitamente pendiente | Definir antes de programar si corresponde devolución, saldo a favor o vale. No inventar una política monetaria. |

## Resultado de auditoría

| Área aclarada | Estado comprobado | Brecha concreta |
|---|---|---|
| Capacidades y límites de planes | Parcial avanzado | Backend protege capacidades, vigencia y sucursales; falta el nuevo esquema Intermedio/chatbot/predicciones y reflejo Mobile. |
| Administración SaaS y tenants | Parcial avanzado | Consola maestra, suspensión, administrador y suscripción existen; falta reporte maestro operativo completo por tenant/sucursal. |
| Roles y sucursales asignadas | Parcial | RBAC y ámbito tenant existen; empleado conserva una sola sucursal principal, no múltiples asignaciones. |
| Jornadas de empleados | Pendiente | No existen jornada medio tiempo/tiempo completo ni tramos horarios por sucursal. |
| Registro de clientes | Parcial | Se acepta `empresa_codigo`; falta selector público con logo/descripción y asociación de una identidad cliente a varios tenants. |
| Medidas y precios por talla | En pruebas | Precio y medidas por variante talla/color/sucursal implementados; falta evidencia E2E desplegada. |
| Traspasos entre sucursales | Pendiente | No existe entidad, API, aprobación, movimiento atómico ni UI. Debe ejecutarse antes de favoritos/calificaciones por prioridad de inventario. |
| Promociones agrupadas | Pendiente | Solo existe promoción a nivel producto; faltan reglas por categoría y temporada. |
| Códigos de descuento | Pendiente | No existe entidad/código aplicable a venta web y presencial. |
| Inventario global y por sucursal | Implementado/en pruebas | Ambos niveles existen y están aislados; los traspasos siguen pendientes. |
| Proveedores y compras | Parcial avanzado | Compra actualiza stock; debe mantenerse la auditoría tenant en nuevas pruebas E2E. |
| Cambios y devoluciones | Parcial | Plazo fijo de 7 días, no configurable por tenant; falta nueva nota de venta, diferencia de precio y sucursal elegible. |
| Reservas por bloques | Parcial | Horario y máximo 3 días se validan; faltan bloques de una hora y ocupación/exclusión concurrente por sucursal/fecha. |
| Venta presencial | Parcial | POS y cliente general existen; falta búsqueda formal por CI y captura de nombre/CI para factura cuando no existe. |
| Envío o recojo | Parcial | Delivery existe; falta alternativa de recojo con bloques de una hora antes del pago. |
| Productos guardados | Pendiente | No existe lista de deseos por cliente/tenant ni accesos Web/Mobile. |
| Pago y tenant | Parcial | Pago deriva de orden/sucursal; falta evidencia de notificación y correo idempotentes por confirmación. |
| Calificaciones y reclamos | Pendiente | No existen entidades, API ni flujo poscompra; debe conservarse una calificación baja aunque se cancele el reclamo sugerido. |

## Dependencias actualizadas

1. Resolver nombres/capacidades finales de los tres planes sin romper contratos existentes.
2. Implementar traspasos de inventario con aislamiento tenant, bloqueo de filas, estados y bitácora.
3. Implementar agenda de bloques de una hora compartida por reservas y recojo.
4. Extender empleados a jornadas y múltiples asignaciones de sucursal.
5. Extender cliente a membresías multi-tenant y selector público de empresa.
6. Completar promociones agrupadas y códigos de descuento.
7. Completar cambios con nota/diferencias monetarias tras definir el caso de menor precio.
8. Implementar favoritos; luego calificaciones/reclamos y notificaciones poscompra.

## Reglas transversales incorporadas

- Toda nueva tabla operativa llevará `empresa_id` e índices de ámbito cuando corresponda.
- El tenant efectivo se derivará del usuario/sesión, nunca de un ID confiado al cliente.
- Los movimientos de stock serán atómicos e idempotentes cuando puedan reintentarse.
- Las migraciones serán aditivas y preservarán filas y contratos existentes.
- Web y Mobile se actualizarán cuando el contrato API afecte a clientes o personal operativo.
