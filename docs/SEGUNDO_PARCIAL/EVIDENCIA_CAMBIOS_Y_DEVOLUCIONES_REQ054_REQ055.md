# Evidencia de Cambios, Devoluciones y Saldos a Favor (REQ-054 y REQ-055)

**Fecha**: 2026-10-22  
**Requisitos**:
- `REQ-054` — Solicitud y liquidación de cambio generan nota vinculada, ajustan inventario y conservan diferencia monetaria.
- `REQ-055` — Cambios y devoluciones con plazo configurable por tenant, cobro de diferencia o saldo a favor, reembolso, sucursal y auditoría por tenant.  
**Estado resultante**: `TERMINADO_VERIFICADO`

---

## 1. Arquitectura y Reglas del Módulo

1. **Plazo Configurable por Tenant (`PUT /api/v1/cambios/politica`)**:
   - Cada tenant puede definir su política de días permitidos para cambios poscompra (`plazo_cambios_dias`, por defecto 7 días).
   - Compras con antigüedad superior al plazo configurado son rechazadas con HTTP 400 Bad Request indicando el límite de días.

2. **Flujo de Solicitud (`POST /api/v1/cambios`)**:
   - El cliente selecciona la orden (`orden_venta_id`), el ítem (`detalle_venta_id`), motivo (`talla_incorrecta`, `defecto_fabrica`, `disconformidad`, etc.), sucursal y fecha programada.
   - Estado inicial: `solicitada`.

3. **Liquidación y Movimiento de Inventario (`POST /api/v1/cambios/{id}/completar`)**:
   - El encargado o administrador aprueba o rechaza (`PUT /api/v1/cambios/{id}/responder`).
   - Al completarse el cambio en tienda física:
     - Si `reponer_prenda_original` es True, la prenda original se restituye al stock de la sucursal.
     - La prenda nueva seleccionada se descuenta atómicamente del inventario.
     - **Prenda de menor valor**: Emite nota de canje `NCJ-XXXXXXXX`, genera saldo a favor para el cliente en `SaldoFavorCliente` y queda disponible en `GET /api/v1/cambios/mi-saldo`.
     - **Prenda de mayor valor**: Exige el cobro presencial de la diferencia (efectivo o QR), rechaza si no hay pago, crea una orden de ajuste y registra el `Pago` correspondiente.
     - Toda la transacción queda vinculada a la orden original y auditada en bitácora por tenant.

---

## 2. Consumo en Web y Mobile

- **Web**:
  - `web/src/app/features/cuenta/mis-compras/`: Botón "Solicitar Cambio" en compras válidas dentro del plazo.
  - `web/src/app/features/admin/cambios/`: Lista administrativa con filtros de sucursal, estado, revisión de motivos y liquidación de diferencias.
- **Mobile**:
  - `mobile/lib/services/order_service.dart`: Método `solicitarCambio()` para clientes.
  - `mobile/lib/config/api_config.dart`: URLs de cambios, política y saldo a favor.

---

## 3. Pruebas Automatizadas

En `backend/tests/test_v6_features.py`:
- `test_cambios_devoluciones_workflow`: Solicitud dentro de 7 días, aprobación, liquidación y rechazo a los 15 días.
- `test_cambio_menor_genera_saldo_y_nota_venta`: Prenda de Bs 150 vs Bs 250 genera saldo a favor de Bs 100 y nota `NCJ-`.
- `test_tenant_configura_plazo_de_cambios`: Actualización de política a 15 días.
- `test_cambio_mayor_exige_y_registra_cobro`: Prenda de Bs 250 vs Bs 100 exige y registra cobro de Bs 150 con orden de ajuste.

---

## 4. Estado de Validación

- Backend: 106 tests pasados (100% éxito).
- Web: Build de producción Angular exitoso sin advertencias.
- Mobile: Flutter analyze 0 issues, tests 9 pasados.
