# Evidencia de límites offline y jerarquía tenant en móvil — REQ-016 y REQ-005

Fecha de verificación: 22/10/2026  
Módulos involucrados: `mobile/`, `backend/`  
Requisitos cubiertos:
- **REQ-016**: PWA y Móvil diferencian comprobante provisional vs. confirmado, bloquean cobros QR/digitales sin conexión y documentan límites operativos de contingencia en modo avión.
- **REQ-005**: Separación estricta de entidad Empresa y Sucursal, con visualización de jerarquía multi-tenant, suscripción, estado y asignación de sucursal en móvil.

---

## 1. Resumen de implementación

### A. REQ-016: Límites de operación offline y bloqueo de cobros digitales en móvil
1. **Bloqueo explícito de cobros QR en modo avión**:
   - En `mobile/lib/screens/catalog/catalog_screen.dart`, el modal de cobro por QR (`_showQrStoreModal`) evalúa reactivamente el estado de red a través de `OfflineSyncService.isOnline`.
   - Si el dispositivo se encuentra sin conexión o en modo avión, se bloquea la apertura del QR bancario y se despliega un diálogo formal informativo:
     > *"El cobro por QR Simple no está disponible sin conexión. En modo avión solo se admiten cobros en efectivo en caja POS local."*
2. **Banner normativo de límites de operación offline**:
   - En `mobile/lib/screens/offline/offline_cash_sale_screen.dart`, se incorporó un panel superior destacado informando los límites operativos:
     - Solo se admiten cobros de contado en efectivo.
     - Métodos de pago electrónicos (QR Simple, pasarelas de pago, tarjetas) quedan estrictamente bloqueados sin red.
     - Se emite un comprobante provisional `LOCAL-XXXXXXXX` y el stock se consolida al reconectar.
3. **Comprobante provisional estructurado**:
   - Al registrar una venta offline en cola SQLite local, la pantalla despliega un modal formal de **Comprobante Provisional**:
     - Código único con prefijo `LOCAL-XXXXXXXX` (primeros 8 caracteres en mayúsculas del UUID).
     - Estado destacado: `PROVISIONAL (OFFLINE)`.
     - Datos de la transacción: Código de cliente, prenda, color, talla, cantidad, total en Bs., efectivo recibido y cambio entregado.
     - Advertencia de stock diferido: la consolidación fiscal y revalidación de existencia se ejecutan automáticamente al reconectar con el backend central.

### B. REQ-005: Visualización jerárquica de Empresa y Sucursales en móvil
1. **Extensión del modelo de usuario**:
   - `mobile/lib/models/user.dart` incorpora `sucursalId` tanto en constructor como en serialización `fromJson` y `toJson`, permitiendo reconocer la sucursal de trabajo asignada para empleados y personal del tenant.
2. **Consultas de contexto tenant y suscripción**:
   - `mobile/lib/services/auth_service.dart`: Incorporados métodos `getTenantDetails()` (consumiendo `GET /api/v1/empresas/mia`) y `getTenantSubscription()` (consumiendo `GET /api/v1/planes/mi-contratacion`).
   - `mobile/lib/config/api_config.dart`: Añadidas URLs `miEmpresaUrl`, `miContratacionUrl`, `authTenantsUrl`, `authTenantsSelectUrl`.
3. **Sección jerárquica en pantalla de perfil**:
   - En `mobile/lib/screens/account/profile_screen.dart`, se implementó la sección **"Jerarquía de Empresa & Sucursales"**:
     - **Card de Empresa**: Nombre de la empresa, código tenant, identificador (`ID #`), estado operativo (`EMPRESA ACTIVA` / `INACTIVA`), plan contratado (badge temático según `Básico`, `Intermedio` o `Profesional`) y rol del usuario.
     - **Listado de Sucursales autorizadas**: Conteo dinámico de sucursales, dirección, teléfono y destaque visual con insignia `TU SUCURSAL` para la sucursal asignada al empleado en sesión (`user.sucursalId`).
     - **Resiliencia offline**: Si se consulta sin conexión, las sucursales se recuperan desde la tabla local SQLite `authorized_branches` con distintivo `SQLite local`.
4. **Selector de Tenant enriquecido**:
   - `mobile/lib/widgets/tenant_switcher.dart`: Menú desplegable muestra el nombre junto a la insignia del código del tenant (`[COD: STYLESTORE]`) y nota de confirmación de aislamiento de datos.

---

## 2. Evidencia de pruebas y análisis

1. **Flutter Analyze**:
   - Comando: `flutter analyze --no-pub`
   - Resultado: **No issues found!** (0 errores, 0 advertencias).
2. **Flutter Test**:
   - Comando: `flutter test --no-pub`
   - Resultado: **100% pasando** (smoke test, pruebas exhaustivas de aislamiento SQLite y pruebas de serialización del modelo de usuario con tenant/sucursal).
