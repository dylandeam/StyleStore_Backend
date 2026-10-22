# Evidencia de Reglas de Planes, Límites de Sucursales y Capacidades IA (REQ-019)

**Fecha**: 2026-10-22  
**Requisito**: `REQ-019` — Básico limita a 2 sucursales sin chatbot/predicciones; Intermedio a 5 con chatbot; Profesional a 10 o más con chatbot/predicciones. Las reglas se protegen en backend y se reflejan en Web/Mobile.  
**Estado resultante**: `TERMINADO_VERIFICADO`

---

## 1. Resumen de Reglas de Negocio Verificadas

| Plan | Cupo Máx. Sucursales | Chatbot Local IA | Predicciones ML / IA Generativa | Protección Backend | Reflejo en Web | Reflejo en Mobile |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Básico** | **2 activas** | ❌ Bloqueado (HTTP 403) | ❌ Bloqueado (HTTP 403) | `PlanService.require_branch_capacity` y `require_capability` | Barra de cupo en lista de sucursales, aviso de cupo alcanzado y modal bloqueado | Insignia de cupo `X / 2` y badge `SIN IA (PLAN BÁSICO)` |
| **Intermedio** | **5 activas** | ✅ Permitido (HTTP 200) | ❌ Bloqueado (HTTP 403) | Enforzado en creación y reactivación de sucursales | Indicador de progreso hasta 5 sucursales | Insignia de cupo `X / 5` y badge `CHATBOT IA ACTIVO` |
| **Profesional** | **10+ activas** | ✅ Permitido (HTTP 200) | ✅ Permitido (HTTP 200) | Enforzado en creación y reactivación | Indicador amplio y desbloqueo de módulos | Insignia de cupo `X / 10+` y badge `IA + PREDICCIONES ACTIVAS` |

---

## 2. Implementación Técnica

### 2.1 Backend (`backend/`)
1. **Protección de reactivación y creación**:
   - `app/services/sucursal_service.py`: En `create_sucursal` y en `update_sucursal` (al reactivar una sucursal inactiva `data.active is True and not sucursal.active`), se invoca `PlanService(self.db).require_branch_capacity(current_user)` que evalúa las sucursales activas contra `contract.plan.max_sucursales`.
2. **Exposición en Contrato de Suscripción**:
   - `app/schemas/plan_suscripcion.py`: Añadidos campos `max_sucursales: int | None` y `capacidades: dict[str, bool] | None` a `ContratacionResponse`.
   - `app/services/plan_service.py`: Enriquecido `serialize_contract` para retornar `max_sucursales` y `capacidades` directamente en `GET /api/v1/planes/mi-contratacion`.
3. **Suite Automatizada E2E (`tests/test_plan_limits_req019.py`)**:
   - `test_req019_basico_branch_limit_and_ai_blocking`:
     - Creación de sucursales 1 y 2 aprobadas (HTTP 201).
     - Intento de 3ra sucursal rechazado con HTTP 403 ("El plan Básico permite hasta 2 sucursales...").
     - Desactivación de sucursal 1 permite registrar la 3ra sucursal.
     - Intento de reactivar la sucursal 1 rechazado con HTTP 403.
     - Chatbot y predicciones rechazados con HTTP 403.
   - `test_req019_intermedio_plan_capabilities`:
     - Admite hasta 5 sucursales activas; la 6ta es rechazada con HTTP 403.
     - Chatbot responde HTTP 200; predicciones rechazadas con HTTP 403.
   - `test_req019_profesional_plan_capabilities`:
     - Admite 10+ sucursales activas.
     - Chatbot y predicciones ML responden HTTP 200.

### 2.2 Frontend Web (`web/`)
1. **Modelos**:
   - `src/app/core/models/plan.model.ts`: Añadidos `max_sucursales` y `capacidades` a la interfaz `PlanContract`.
2. **Gestión de Sucursales (`src/app/features/admin/sucursales/`)**:
   - `sucursales-list.component.ts`: Inyección de `PlanesService`, consumo de `getMyContract()`, cálculo reactivo de `activeBranchesCount`, `maxBranches` y bandera `isQuotaReached`.
   - `sucursales-list.component.html`: Banner destacado de cupo de sucursales con barra de ocupación porcentual (`quota-bar-fill`), insignia del plan contratado y alerta de cupo completo con enlace directo a `/planes`.
   - `sucursales-list.component.css`: Estilos visuales con badges clasificados por plan (`plan-basico`, `plan-intermedio`, `plan-profesional`), animaciones suaves y advertencia ámbar en saturación.

### 2.3 Mobile Flutter (`mobile/`)
1. **Perfil y Jerarquía SaaS (`lib/screens/account/profile_screen.dart`)**:
   - Incorporada insignia reactiva de cupo en la tarjeta de empresa:
     `CUPO SUCURSALES: X / Y SUCURSALES` (calculado con `_branches.where((b) => b['active'] != false).length` y `max_sucursales` del contrato).
   - Insignias de capacidades de Inteligencia Artificial:
     - Profesional: `IA + PREDICCIONES ACTIVAS` (Verde esmeralda).
     - Intermedio: `CHATBOT IA ACTIVO` (Verde esmeralda).
     - Básico: `SIN IA (PLAN BÁSICO)` (Gris atenuado con icono de candado).

---

## 3. Resultados de Pruebas y Builds

1. **Backend Tests**:
   ```
   tests/test_plan_limits_req019.py: 3 passed
   Full Backend Suite: 106 passed, 2 warnings in 83.55s
   ```
2. **Frontend Web Build**:
   ```
   npx ng build --configuration production
   Application bundle generation complete (1.82 MB, 0 errores, main-4SBJO6QY.js)
   ```
3. **Mobile Analysis & Tests**:
   ```
   flutter analyze --no-pub: No issues found! (ran in 5.1s)
   flutter test --no-pub: All 9 tests passed!
   ```
