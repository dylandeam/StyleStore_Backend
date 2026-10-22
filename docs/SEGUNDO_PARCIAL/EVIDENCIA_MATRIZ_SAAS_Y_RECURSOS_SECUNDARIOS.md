# Evidencia — Matriz SaaS Tenant/Sucursal/Plan y Aislamiento de Recursos Secundarios (REQ-014 y REQ-017)

Fecha de verificación: 22/10/2026  
Módulos involucrados: `backend/`, `web/`  
Requisitos cubiertos:
- **REQ-014**: Consola maestra SaaS protegida por `is_platform_admin`, auditoría de cambios y matriz operativa integral de Tenant / Sucursal / Plan con cupos y capacidades.
- **REQ-017**: Consola maestra para ciclo de vida de tenants (crear, editar, suspender, reactivar, gestionar administrador) con trazabilidad y asociación aislada de recursos secundarios (archivos persistentes en BD, próximos lanzamientos y trabajos de prueba virtual).

---

## 1. Alcance técnico implementado

### A. Backend (`app/services/empresa_service.py` y `app/schemas/empresa.py`)
1. **Esquema enriquecido `EmpresaResumenResponse`**:
   - `archivos_count`: Conteo de archivos persistentes subidos pertenecientes exclusivamente al tenant (`UploadedFile.empresa_id`).
   - `proximamente_count`: Conteo de prendas de próximos lanzamientos registradas bajo el tenant (`Proximamente.empresa_id`).
   - `pruebas_virtuales_count`: Conteo de sesiones y fotos de probador virtual asociadas al tenant (`PruebaVirtual.empresa_id`).
   - `capacidades`: Esquema `TenantCapacidadesResponse` con:
     - `chatbot`: `True` para planes Intermedio y Profesional, `False` para Básico.
     - `predicciones`: `True` exclusivamente para plan Profesional.
     - `max_sucursales`: 2 (Básico), 5 (Intermedio), 10+ (Profesional).
     - `cupo_sucursales_disponible`: Cálculo seguro `max(0, max_sucursales - sucursales_count)`.
2. **Seguridad y auditoría**:
   - Acceso exclusivo con `require_platform_admin`. Rechazo HTTP 403 / 401 para cualquier rol empresarial tenant.
   - Bitácora inmutable en `BitacoraService` por cada alta, edición, suspensión o reactivación.

### B. Frontend Web (`web/src/app/features/admin/tenants/`)
1. **Selector de visualización**:
   - Toggle interactivo en la barra de herramientas: **▦ Tarjetas** vs. **⊞ Matriz Tenant / Plan / Sucursales**.
2. **Matriz Operativa Completa (`viewMode === 'matrix'`)**:
   - Tabla responsiva con columnas:
     - **Empresa / Tenant**: Avatar, nombre y código monospace.
     - **Plan Contratado**: Badge con color semántico según nivel (`basico`, `intermedio`, `profesional`), vigencia y estado.
     - **Sucursales & Cupo**: Medidor visual de porcentaje de ocupación con barra de progreso y etiqueta de disponibilidad (`X / Y cupos`).
     - **Capacidades IA**: Badges reactivos de `Chatbot` y `Predicciones ML` según plan.
     - **Recursos Secundarios**: Conteo de archivos persistentes 📁, próximos lanzamientos 🚀 y pruebas virtuales 👗.
     - **Usuarios**: Conteo de cuentas vinculadas.
     - **Administrador**: Nombre y correo del responsable tenant.
     - **Estado**: Badge activo/suspendido.
     - **Acciones**: Desplegar detalles, editar datos de empresa, gestionar administrador y suspender/reactivar.
3. **Sección de Recursos Secundarios en panel desplegable**:
   - Sección dedicada en vista tarjetas y matriz mostrando el desglose de los recursos secundarios del tenant y sus capacidades activas.

---

## 2. Evidencia de pruebas y compilación

1. **Backend Tests**:
   - `pytest tests/test_tenant_foundation.py -q`: 14 pruebas pasando.
   - Suite completa `pytest -q`: 103 pruebas pasando al 100%.
2. **Web Build**:
   - `npm run build`: Compilación de producción exitosa en Angular 21 (`main-YHJ7X3K4.js`, 1.81 MB, 0 errores).
