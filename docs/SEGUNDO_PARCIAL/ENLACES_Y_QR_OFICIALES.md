# Enlaces Oficiales y Códigos QR de Acceso — StyleStore SaaS

Fecha de verificación: 21/10/2026.  
Requisito Matriz: `REQ-053 [P1]`.  
Propósito: Proveer el acceso verificado y escaneable a todas las plataformas del ecosistema para la evaluación y defensa del segundo parcial.

---

## 1. Directorio de Enlaces y Códigos QR

### 1.1. Aplicación Web Progresiva (PWA) — Producción Vercel
- **URL Pública:** [`https://style-store-frontend-nine.vercel.app`](https://style-store-frontend-nine.vercel.app)
- **Estado de Despliegue:** Activo y verificado (sirviendo bundle Angular 21 `main-S46ZNSZX.js`).
- **Capacidades Verificables:** Catálogo multitenant, instalación como PWA con Service Worker, persistencia offline en IndexedDB, módulo de reportes interactivos SVG, comparativa de sucursales y checkout con PayPal Sandbox.
- **Código QR:** [`qr_web_pwa.svg`](file:///d:/Descargas/Proyecto%20Examen%20StyleStore/backend/docs/SEGUNDO_PARCIAL/qr_web_pwa.svg)

```text
       QR Code — Frontend Web PWA (Vercel)
       Scan with any camera or mobile device:
       https://style-store-frontend-nine.vercel.app
```

---

### 1.2. Backend API y Documentación Interactiva Swagger (Railway)
- **URL Base:** [`https://web-production-07e73.up.railway.app`](https://web-production-07e73.up.railway.app)
- **Documentación Swagger / OpenAPI:** [`https://web-production-07e73.up.railway.app/docs`](https://web-production-07e73.up.railway.app/docs)
- **Documentación ReDoc:** [`https://web-production-07e73.up.railway.app/redoc`](https://web-production-07e73.up.railway.app/redoc)
- **Código QR:** [`qr_backend_docs.svg`](file:///d:/Descargas/Proyecto%20Examen%20StyleStore/backend/docs/SEGUNDO_PARCIAL/qr_backend_docs.svg)

```text
       QR Code — Backend API Swagger Docs (Railway)
       Scan to explore endpoints, schemas and security:
       https://web-production-07e73.up.railway.app/docs
```

---

### 1.3. Aplicación Móvil Android (Flutter APK Release)
- **Paquete Compilado:** `mobile/build/app/outputs/flutter-apk/app-release.apk`
- **Versión de Release:** `1.0.3+4`
- **Validación en Dispositivo Físico:** Instalado y probado exitosamente en Samsung Galaxy S21+ (Android 14) con persistencia SQLite y modo avión (`EVIDENCIA_APK_2026-10-20.md`).
- **Instrucciones de Instalación:**
  1. Habilitar la instalación de orígenes desconocidos en el dispositivo Android.
  2. Descargar o transferir `app-release.apk` al teléfono.
  3. Ejecutar el instalador de paquetes de Android y confirmar la instalación.
  4. Al iniciar la aplicación, `api_config.dart` conectará automáticamente mediante fallback al servidor en la nube o red local.

---

### 1.4. Repositorios de Código Fuente en GitHub
- **Backend (FastAPI + SQLAlchemy + PostgreSQL):**  
  [`https://github.com/dylandeam/StyleStore_Backend.git`](https://github.com/dylandeam/StyleStore_Backend.git) (Rama `main`)
- **Frontend Web (Angular 21 + PWA):**  
  [`https://github.com/dylandeam/StyleStore_Frontend.git`](https://github.com/dylandeam/StyleStore_Frontend.git) (Rama `main`)
- **Mobile (Flutter + SQLite):**  
  [`https://github.com/dylandeam/StyleStore_Mobile.git`](https://github.com/dylandeam/StyleStore_Mobile.git) (Rama `main`)
- **Código QR del Repositorio:** [`qr_repo_github.svg`](file:///d:/Descargas/Proyecto%20Examen%20StyleStore/backend/docs/SEGUNDO_PARCIAL/qr_repo_github.svg)

---

## 2. Credenciales y Datos Demostrativos para Evaluación

| Rol | Correo Electrónico | Contraseña | Alcance y Funcionalidades |
|---|---|---|---|
| **Administrador SaaS** | `admin@stylestore.com` | `admin123` | Supervisión de todos los tenants, creación de planes y empresas, respaldos globales |
| **Administrador Tenant** | `admin.empresa@stylestore.com` | `tenant123` | Gestión de sucursales, empleados, catálogo, reportes y comparativas de su empresa |
| **Encargado de Tienda** | `encargado.central@stylestore.com` | `encargado123` | Control de stock físico y retiro en sucursal |
| **Cajero POS** | `cajero.sucursal1@stylestore.com` | `cajero123` | Caja presencial, cobro en efectivo / QR y cola offline |
| **Cliente Comprador** | `cliente1@stylestore.com` | `cliente123` | Catálogo, favoritos, compras online, historial y calificaciones |
| **PayPal Sandbox** | `comprador.sandbox@stylestore.com` | `SandboxPass2026!` | Cuenta pagadora para simulación de checkout electrónico |
