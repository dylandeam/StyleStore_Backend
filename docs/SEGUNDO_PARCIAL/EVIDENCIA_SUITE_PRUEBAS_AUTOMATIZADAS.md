# Evidencia de la Suite de Pruebas Automatizadas — StyleStore SaaS

Fecha de ejecución: 21/10/2026.  
Requisito Matriz: `REQ-051 [P1]`.  
Propósito: Documentar la cobertura, módulos probados y comandos de reproducción de la batería de pruebas unitarias y de integración.

---

## 1. Resumen de Ejecución de Pruebas

| Plataforma | Herramienta | Pruebas Ejecutadas | Aprobadas | Falladas | Tiempo de Ejecución |
|---|---|---|---|---|---|
| **Backend API** | `pytest 8.3.3` | **97** | **97** (100%) | 0 | 69.19 s |
| **Mobile App** | `flutter test 3.24+` | **5** | **5** (100%) | 0 | 8.42 s |
| **Análisis Estático Mobile** | `flutter analyze` | Reglas oficiales | 0 issues | 0 | 4.10 s |
| **Compilación Frontend Web** | `ng build` (Angular 21) | Build de producción | Exitoso | 0 | 13.34 s |

---

## 2. Cobertura de Pruebas Backend por Módulo Crítico

```text
tests/
├── test_auth.py                              # Login, JWT, refresh tokens, expiración y blacklist
├── test_roles_permisos.py                    # RBAC granular, requires_permission y platform admin
├── test_multiempresa_aislamiento.py          # Aislamiento A/B de catálogo, clientes y sucursales
├── test_planes_capacidades.py                # Reglas de 3 planes, límites de sucursales e IA
├── test_conflictos_stock_sync.py             # Sincronización offline, concurrencia y sobreventa
├── test_pago_confirmacion_idempotente.py     # Cierre atómico de pago, deduplicación de correo y recibos
├── test_reportes_multiempresa_comparativa.py # Comparativa de sucursales REQ-063 y rechazo 404 a sondas
├── test_ml_reproducible.py                   # Semilla fija, dataset sintético, Ridge y K-means
├── test_cambios_devoluciones_liquidacion.py  # Plazos de cambio, saldo a favor y ajuste de stock
├── test_favoritos_tenant.py                  # Aislamiento de prendas guardadas por empresa
└── test_recursos_secundarios_tenant.py       # Aislamiento de uploaded_files, proximamente y prueba virtual
```

---

## 3. Comandos de Reproducción Local

### 3.1. Backend
```powershell
cd "D:\Descargas\Proyecto Examen StyleStore\backend"
.\.venv\Scripts\Activate.ps1
pytest -q
```
**Salida verificada:**
```text
........................................................................ [ 74%]
.........................                                                [100%]
97 passed, 2 warnings in 69.19s
```

### 3.2. Mobile
```powershell
cd "D:\Descargas\Proyecto Examen StyleStore\mobile"
flutter analyze --no-pub
flutter test --no-pub
```
**Salida verificada:**
```text
Analyzing mobile...
No issues found! (ran in 4.1s)

00:08 +5: All tests passed!
```

### 3.3. Frontend Web
```powershell
cd "D:\Descargas\Proyecto Examen StyleStore\web"
npm.cmd run build
```
**Salida verificada:**
```text
Application bundle generation complete. [13.338 seconds]
Output location: D:\Descargas\Proyecto Examen StyleStore\web\dist\web-app
```
