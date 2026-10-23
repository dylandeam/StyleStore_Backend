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

## Evidencia automatizada

- Backend: **120 pruebas aprobadas**; incluye regresiones de aislamiento, concurrencia de
  stock, idempotencia offline, vencimiento/renovación, PayPal fail-closed y push multi-tenant.
- Web: **2 pruebas aprobadas** y build de producción exitoso (`main-XMQOKW2X.js`).
- Mobile: `flutter analyze` sin incidencias, **9 pruebas aprobadas** y APK debug generado en
  `build/app/outputs/flutter-apk/app-debug.apk` (versión `1.0.4+5`).
- Migraciones: una única cabeza Alembic; la migración de push agrega `empresa_id` a
  notificaciones y crea `push_devices`.

## Verificación externa que no puede falsificarse

El código y las pruebas locales no sustituyen credenciales ni dispositivos reales. Antes de
declarar producción totalmente operativa se debe:

1. Configurar credenciales PayPal Sandbox/Live válidas en Railway, manteniendo
   `ALLOW_MOCK_PAYPAL=false`, y completar una compra y una suscripción reales.
2. Configurar Firebase según `mobile/FIREBASE_PUSH_SETUP.md` y probar recepción en un teléfono
   con la app abierta, en segundo plano y cerrada.
3. Ejecutar `alembic upgrade head` durante el despliegue de Railway.
4. Verificar las URLs desplegadas después de que Railway procese el commit más reciente.

Estas tareas están marcadas como validación externa, no como funcionalidad simulada.
