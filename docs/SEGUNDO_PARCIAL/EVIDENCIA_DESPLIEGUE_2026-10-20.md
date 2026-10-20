# Evidencia de despliegue — 20 de octubre de 2026

Verificación realizada después de publicar `main` en los tres repositorios:

| Componente | URL comprobada | Resultado |
|---|---|---|
| API OpenAPI | `https://web-production-07e73.up.railway.app/openapi.json` | HTTP 200; contiene `/api/v1/sync/operations` y `/api/v1/planes` |
| Planes públicos | `https://web-production-07e73.up.railway.app/api/v1/planes` | HTTP 200; exactamente 3 planes |
| Seguridad sync | `POST /api/v1/sync/operations` sin JWT | HTTP 401 |
| PWA | `https://style-store-frontend-nine.vercel.app/` | HTTP 200; título nuevo desplegado |
| Manifest | `/manifest.webmanifest` | `application/manifest+json`; nombre `StyleStore` |
| Service Worker | `/ngsw.json` | configuración Angular SW versión 1 disponible |
| Contrato IA protegido | `/openapi.json` tras `2788225` | HTTP 200; `ConsultaReporteIARequest` publicado con máximo de 500 caracteres |
| Mensaje de plan en PWA | `/` tras `379251e` | HTTP 200; bundle desplegado `main-GTIYOVVY.js` |

La batería posterior a la protección de reportes aprobó `61` pruebas backend.
Incluye rechazo por rol, rechazo para plan Básico, acceso para Profesional y
aislamiento del contexto analítico entre empresas A/B. El build Angular de
producción y sus `2` pruebas también aprobaron antes del despliegue.

El dominio histórico `stylestorebackend-production.up.railway.app` de la guía devuelve actualmente `Application not found`. El frontend configurado y operativo consume `web-production-07e73.up.railway.app`; no se cambió el dominio sin autorización funcional, pero se deja registrada la diferencia para corregir documentación/infraestructura final.

Pendiente de evidencia manual: instalación desde navegador, recarga sin red, cierre/reapertura con IndexedDB/SQLite y APK actualizado en dispositivo.
