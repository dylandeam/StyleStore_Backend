# Evidencia E2E de renovación PayPal Sandbox — 25/10/2026

## Objetivo

Comprobar en la infraestructura desplegada que un administrador de tenant puede cambiar o
renovar su plan únicamente después de un cobro aprobado y capturado por PayPal, sin dinero
real, sin modo mock y sin modificar directamente el contrato.

## Entorno y condiciones

- Backend productivo de demostración desplegado en Railway.
- PayPal oficial en modo `sandbox` y `ALLOW_MOCK_PAYPAL=false`.
- Tenant: `Ropa_Varones` (empresa 2).
- Administrador tenant autenticado: usuario 6.
- Cambio solicitado: Básico -> Intermedio.
- Precio comercial definido por SaaS: Bs 200.
- Conversión de demostración: 11 BOB/USD, porque PayPal no procesa BOB.
- Importe enviado y mostrado por PayPal: USD 18.18.
- Medio de prueba: tarjeta estática oficial de PayPal Sandbox; no se usó dinero real.

No se documentan Client ID, Secret, contraseñas ni números completos de credenciales de
prueba.

## Resultado verificable

1. El backend creó una contratación pendiente y una orden oficial Sandbox
   `2G248470C8077533A`.
2. PayPal aprobó la fuente de pago y la captura devolvió estado `COMPLETED`.
3. La captura `7CA03993MB8748641` informó exactamente USD 18.18, igual al importe esperado
   por la lógica de conversión.
4. Solo después de validar estado, moneda e importe, `PlanService.activate_paid_contract`
   activó el contrato 6.
5. La consulta posterior en la base desplegada confirmó:
   - contrato 3 / Básico: `reemplazada`, `pagado`;
   - contrato 6 / Intermedio: `activa`, `pagado`;
   - vigencia nueva: 25/10/2026 al 24/11/2026;
   - tenant `Ropa_Varones`: `active=True`.
6. Los intentos pendientes anteriores permanecen cancelados y no activaron ningún plan.

## Conclusión

REQ-022 y REQ-073 quedan verificados de extremo a extremo. El precio continúa administrado
en BOB dentro de StyleStore, PayPal recibe su equivalente USD y el tenant no obtiene el plan
ni se reactiva antes de una captura oficial `COMPLETED`.
