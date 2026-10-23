# Auditoría integral de cierre — 22/10/2026

## Alcance revisado

Se contrastaron el PDF oficial del segundo parcial, los requisitos adicionales SaaS y los
tres repositorios (`backend`, `web`, `mobile`). La revisión cubrió autenticación, aislamiento
multi-tenant, planes y vencimiento, PayPal, catálogo, inventario, ventas/POS, reservas,
delivery, pagos, notificaciones, sincronización offline, reportes/IA y presentación
responsiva.

## Hallazgos corregidos

1. **PayPal móvil simulado:** se eliminó el formulario que imitaba el login de PayPal, las
   credenciales de prueba incrustadas y el token `MOCK_TOKEN`. La app abre ahora la URL de
   aprobación emitida por PayPal y captura únicamente el ID real de esa orden.
2. **PayPal fail-closed:** compras y suscripciones rechazan credenciales mock, IDs mock y
   fallos OAuth/API. La simulación solo existe si `ALLOW_MOCK_PAYPAL=true`, valor reservado
   para la suite automatizada.
3. **Sesiones multi-tenant concurrentes:** seleccionar una empresa ya no sobrescribe
   `users.empresa_id`. El tenant activo se toma del JWT, se valida contra `user_empresas` y
   permanece en el refresh token. Dos dispositivos pueden mantener tenants diferentes sin
   invalidarse.
4. **Notificaciones push:** se añadió registro de dispositivos por tenant/usuario, Firebase
   Admin en backend, FCM en Flutter, canal Android, permiso Android 13+, background mode iOS,
   notificación visible en primer plano y navegación al tocarla.
5. **Navegación web:** se eliminó la repetición de gestión de planes para el administrador
   SaaS y se agruparon las entradas según plataforma, tienda y administración.
6. **Tablas responsivas:** las tablas web pueden desplazarse horizontalmente en pantallas
   estrechas y conservan visibles las acciones; promociones recibió el contenedor que le
   faltaba.
7. **Interfaz móvil:** inicio profesional con navegación inferior, anchura adaptada para
   tablet, acciones que se redistribuyen sin overflow y terminología propia de Delivery
   StyleStore.
8. **Persistencia de sesión:** se conserva el access/refresh token en almacenamiento seguro;
   al abrir la app se restaura la sesión y se vuelve a registrar el dispositivo push.
9. **Deriva real del esquema Railway:** el smoke test desplegado detectó HTTP 500 en
   `/reservas/mias` porque la base estaba marcada/operando sin columnas de revisiones
   posteriores. La migración defensiva `4f6a8b012345` (`c185d2e`) repara únicamente campos,
   índices, relaciones y nulabilidad ausentes. Tras el despliegue, reservas, catálogo, pagos,
   notificaciones y sync responden 200 para los tenants `stylestore` y `varones`.

## Garantías multi-tenant revisadas

- El tenant operativo se deriva del token autenticado y no de IDs enviados por el cliente.
- Las membresías múltiples de clientes se validan antes de emitir tokens de otro tenant.
- Pagos y notificaciones contienen `empresa_id` obligatorio.
- Dispositivos push se consultan por `empresa_id + user_id`.
- Administrador SaaS supervisa tenants; administrador empresarial opera únicamente su
  empresa y sucursales.
- La expiración de la contratación inactiva el tenant; solo el administrador conserva la
  superficie mínima necesaria para pagar la renovación. La activación ocurre después de una
  captura PayPal `COMPLETED`.

## Evidencia automatizada (actualizada 23/10/2026)

- Backend: **122 pruebas aprobadas**; incluye regresiones de aislamiento, concurrencia de
  stock, idempotencia offline, vencimiento/renovación, PayPal fail-closed y push multi-tenant.
- Web: **2 pruebas aprobadas** y build de producción exitoso (`main-XMQOKW2X.js`).
- Mobile: `flutter analyze` sin incidencias, **9 pruebas aprobadas** y APK debug generado en
  `build/app/outputs/flutter-apk/app-debug.apk` (versión `1.0.4+5`).
- Migraciones: una única cabeza Alembic `4f6a8b012345`; además de push multi-tenant, incluye
  reparación idempotente para bases que fueron marcadas sin ejecutar todo el DDL histórico.

## Verificación externa que no puede falsificarse

El código y las pruebas locales no sustituyen credenciales ni dispositivos reales. Antes de
declarar producción totalmente operativa se debe:

1. Completar una compra y una suscripción con la configuración oficial PayPal Sandbox
   ya desplegada en Railway, manteniendo `ALLOW_MOCK_PAYPAL=false`.
2. Configurar Firebase según `mobile/FIREBASE_PUSH_SETUP.md` y probar recepción en un teléfono
   con la app abierta, en segundo plano y cerrada.
3. Configurar SMTP en Railway y comprobar la entrega real y única del correo de pago.

Railway ya ejecuta `alembic upgrade head`, publica los endpoints nuevos y el 23/10/2026
desplegó correctamente las cinco variables oficiales de PayPal Sandbox: Client ID/Secret,
`PAYPAL_MODE=sandbox`, `ALLOW_MOCK_PAYPAL=false` y `PAYPAL_BOB_PER_USD=11.00`. Los secretos
no se registran en el repositorio ni en esta evidencia. La conversión de los precios BOB a USD
se realiza mediante `PAYPAL_BOB_PER_USD` porque PayPal no admite BOB. En el Samsung físico se
confirmó la persistencia de sesión, el carrito con una prenda en stock y la pantalla de checkout
de delivery hasta el botón final de PayPal.

La primera prueba física descubrió que el endpoint de compras omitía `currency="BOB"` al crear
la orden: PayPal interpretaba Bs. 77.69 como USD 77.69. Se corrigió para convertir ese total a
USD; con la tasa inicial de 6.96 el resultado era USD 11.16. La app muestra ambos importes,
permite reintentar una orden
`pendiente_pago` sin volver a descontar stock y el backend traduce `ORDER_NOT_APPROVED` y
`PAYMENT_DENIED` a mensajes accionables sin exponer el JSON interno de PayPal.

Para corregir el rechazo del comercio boliviano se creó una cuenta **Business Sandbox US**,
se asoció la aplicación `StyleStoreUS` y se rotaron sus credenciales exclusivamente en
Railway. El servicio volvió a estado `Online` y el correo de acceso de la cuenta de prueba
quedó como `stylestore1@gmail.com`. Con la tasa de demostración configurada en `11.00`, el
total local de Bs. 77.69 se presenta a PayPal como USD 7.06. El comprador Personal Sandbox
aprobó la orden en el Samsung y la captura terminó correctamente: ORD-2 cambió a `PAGADA`,
se emitió `REC-00000002` con estado `APROBADO`, se abrió el rastreo de delivery y el catálogo
mostró 3 unidades restantes (5 iniciales menos las unidades comprometidas por ORD-1 y ORD-2).
No se creó un tercer pedido. Esta documentación no contiene contraseñas, Client IDs ni secretos.

Estas tareas están marcadas como validación externa, no como funcionalidad simulada.
