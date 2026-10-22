# Paquetes de Entrega y Cronograma Oficial — StyleStore SaaS (Segundo Parcial)

Fecha de consolidación: 21/10/2026.  
Requisito Matriz: `REQ-052 [P1]`.  
Propósito: Estructuración formal de los cuatro paquetes de entrega y defensa para la cátedra de Sistemas de Información II.

---

## 1. Cronograma Oficial de Entregas y Hitos de Evaluación

```mermaid
gantt
    title Cronograma de Entregas Oficiales — Segundo Parcial
    dateFormat  YYYY-MM-DD
    section Entregas Oficiales
    Entrega 1 : Fundamentos & ICONIX       :done,    ent1, 2026-10-19, 2026-10-25
    Entrega 2 : SaaS, Offline & Sync        :done,    ent2, 2026-10-25, 2026-11-01
    Entrega 3 : BI, ML & Post-Venta         :active,  ent3, 2026-11-01, 2026-11-08
    Defensa Final : Demostración en Vivo    :crit,    def,  2026-11-08, 2026-11-10
```

---

## 2. Detalle de Paquetes de Entrega

### Paquete 1: Presentación 1 — Domingo 25 de Octubre de 2026
**Eje Temático:** Arquitectura Base, Fundamentos Multi-tenant y Análisis ICONIX.
- **Entregables de Documentación:**
  - `backend/docs/SEGUNDO_PARCIAL/INVENTARIO_TECNICO.md`: Diagnóstico y contraste de los tres repositorios.
  - `backend/docs/SEGUNDO_PARCIAL/ARTEFACTOS_ICONIX_UML25.md` (Secciones 1 a 3): Modelo de Dominio conceptual, Glosario y Diagrama de Casos de Uso.
- **Entregables de Software:**
  - Modelos relacionales con discriminador `empresa_id` obligatorio.
  - Migración Alembic aditiva con cabeza única.
  - Consola maestra de administración de empresas (SaaS Admin).
  - Pruebas automatizadas de aislamiento multi-tenant.

---

### Paquete 2: Presentación 2 — Domingo 01 de Noviembre de 2026
**Eje Temático:** Planes de Suscripción, Operaciones Offline y Protocolo de Sincronización.
- **Entregables de Documentación:**
  - `backend/docs/SEGUNDO_PARCIAL/CONTRATO_SINCRONIZACION.md`: Especificación técnica del contrato `/sync` con UUID v4 y semántica idempotente.
  - `backend/docs/SEGUNDO_PARCIAL/EVIDENCIA_REEMBOLSOS_OFFLINE.md`: Protocolo de manejo de sobreventas y reembolsos auditables.
- **Entregables de Software:**
  - Angular 21 transformado en Progressive Web App (PWA) con Service Worker e IndexedDB.
  - Aplicación Flutter con motor relacional local SQLite (`stylestore.db`).
  - Tres planes configurables (Básico, Intermedio, Profesional) con control de cuotas y capacidades.
  - Demostración de venta al contado y reserva en modo avión.

---

### Paquete 3: Presentación 3 — Domingo 08 de Noviembre de 2026
**Eje Temático:** Inteligencia de Negocios, Machine Learning Reproducible y Procesos de Post-Venta.
- **Entregables de Documentación:**
  - `backend/docs/SEGUNDO_PARCIAL/EVIDENCIA_REPORTES_COMPARATIVOS_GRAFICOS.md`: Comparativa entre sucursales y gráficos interactivos SVG.
  - `backend/docs/SEGUNDO_PARCIAL/EVIDENCIA_ML_REPRODUCIBLE.md`: Modelos supervisados (Ridge) y no supervisados (K-means).
  - `backend/docs/SEGUNDO_PARCIAL/EVIDENCIA_CONFIRMACION_PAGOS.md`: Confirmación y recibo idempotente de pagos.
- **Entregables de Software:**
  - Dashboard interactivo con gráficos SVG nativos Donut y barras de rendimiento por sucursal.
  - Exportación en streaming de reportes consolidados a Excel y PDF.
  - Módulo de cambios con liquidación de diferencias y ledger de saldo a favor.
  - Notificaciones automáticas y evaluación poscompra.

---

### Paquete 4: Defensa Final — Martes 10 de Noviembre de 2026 (07:00 AM)
**Eje Temático:** Validación Global en Vivo, Cobertura de Pruebas y Despliegue Público.
- **Entregables de Documentación:**
  - `backend/docs/SEGUNDO_PARCIAL/DOCUMENTO_FINAL_CAPITULOS_I_VI.md`: Documento maestro de tesis/proyecto con Capítulos I a VI.
  - `backend/docs/SEGUNDO_PARCIAL/EVIDENCIA_RNF01_RNF12.md`: Matriz de verificación técnica de los 12 RNF.
  - `backend/docs/SEGUNDO_PARCIAL/ENLACES_Y_QR_OFICIALES.md`: URLs públicas y códigos QR escaneables.
- **Entregables de Software:**
  - Suite de 97 pruebas backend aprobadas en `pytest -q`.
  - 5 pruebas unitarias móviles aprobadas en `flutter test --no-pub`.
  - Frontend Web PWA en producción Vercel (`https://style-store-frontend-nine.vercel.app`).
  - Backend API en producción Railway (`https://web-production-07e73.up.railway.app`).
  - APK Release `1.0.3+4` para Android.
