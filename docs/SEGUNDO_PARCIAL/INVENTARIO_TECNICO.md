# Inventario técnico verificado — segundo parcial

Fecha de corte: 20/10/2026. Fuente operativa: código de las ramas `main` de Backend, Frontend y Mobile.

## Resultado de auditoría

| Área | Evidencia real | Diferencia frente al plan |
|---|---|---|
| Backend | FastAPI, SQLAlchemy, JWT access/refresh/blacklist, RBAC, 31 routers funcionales, PostgreSQL/Alembic | Antes de este corte no existía entidad empresa, aislamiento tenant, planes SaaS ni contrato sync general |
| Datos | 40+ modelos para usuarios, catálogo, stock, carrito, ventas, pagos, reservas, delivery, cambios, notificaciones, reportes y AR | La cadena Alembic solo cubría hasta v5; varias ampliaciones posteriores dependían de DDL defensivo en `init_db.py` |
| Web | Angular 21 standalone, guards, interceptor JWT, catálogo, administración, pagos, reportes, delivery y vestidor | No era PWA, no tenía Service Worker, Manifest comercial, IndexedDB ni cola offline |
| Mobile | Flutter + Provider + secure storage, fallback multi-host, refresh JWT, catálogo, carrito, pedidos, PayPal, delivery, chatbot y vestidor | No tenía SQLite, cola offline ni sincronización comercial |
| Reportes | Vista previa y exportación Excel/PDF para múltiples familias; consultas y agregados limitados al tenant | Falta autorización por plan, evidencia de voz y cuatro escenarios multiempresa completos |
| ML | Recomendaciones heurísticas/IA y análisis de prendas | No existen dataset reproducible ni modelos supervisado/no supervisado entrenados |
| Documentación | Guías y especificaciones históricas en la carpeta raíz | No existían artefactos ICONIX/UML del segundo parcial ni matriz viva de evidencias |
| Despliegue | Remotos GitHub configurados; URLs Railway/Vercel declaradas en guía | El despliegue no se modifica automáticamente con un commit local; falta verificar pipeline/push y APK final |

## Migraciones verificadas

Cadena lineal antes del segundo parcial:

1. `a26a7c0a497a`: usuarios y blacklist.
2. `b37b8d0e518c`: permisos, bitácora, sucursales y productos iniciales.
3. `c48a9e102f4a`: entidades v4, variantes y stock.
4. `d59b0f213a5b`: roles dinámicos y entidades comerciales v5.
5. `e7a1c4b9d210`: base aditiva empresa/tenant incorporada en este corte.
6. `f28b6d91a043`: horarios configurables de sucursal y fecha/hora de retiro.
7. `a41c7e9d2b65`: ámbito empresa en catálogo, proveedores, QR y bitácora.
8. `b52d8f1a3c74`: tres planes configurables por ámbito y contrataciones con snapshot.

Existe una sola cabeza Alembic (`b52d8f1a3c74`). La generación SQL de upgrade y downgrade fue comprobada; las migraciones conservan datos históricos asignándolos a la empresa legado `stylestore`.

## Seguridad y permisos comprobados

- El JWT se obtiene del servidor y el backend resuelve el usuario actual; el cliente no decide el tenant efectivo.
- El claim `empresa_id` se contrasta con la asignación vigente del usuario.
- Se separó administrador global de plataforma (`is_platform_admin`) y administrador de empresa.
- La creación de empresas está reservada al administrador global.
- Usuarios, sucursales, catálogo, proveedores, stock, carrito, ventas, compras, pagos, envíos, cambios, bitácora, dashboard y reportes se filtran por empresa o por sus sucursales.
- Las referencias cruzadas de catálogo y las lecturas directas de recursos operativos ajenos devuelven 404.
- Hay pruebas negativas A/B para sucursales, usuarios, personal, clientes, catálogo, proveedores, inventario, ventas, pagos, envíos, dashboard y reporte de ventas.
- La cobertura de archivos, respaldos globales y algunos recursos secundarios aún debe cerrarse; por eso REQ-006/007 permanecen `EN_CURSO`.

## Regresiones preservadas

Se conservaron sin cambiar contratos existentes: PayPal Sandbox, QR de mostrador, checkout con bloqueo de stock, delivery/rastreo, bitácora, catálogo, promociones, chatbot, outfits y vestidor virtual. Su validación automatizada no sustituye la prueba manual de producción.

## Comandos de evidencia

```powershell
# Backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic heads

# Web
.\node_modules\.bin\ng.cmd test --watch=false
.\node_modules\.bin\ng.cmd build

# Mobile
flutter analyze --no-pub
flutter test --no-pub
```

## Riesgos abiertos

- Falta cerrar aislamiento de archivos, respaldos globales y recursos secundarios antes de declarar completa la frontera tenant.
- DDL histórico en `init_db.py` debe trasladarse gradualmente a migraciones controladas.
- Credenciales demostrativas visibles en código histórico deben salir a variables de entorno antes de producción real.
- Faltan PWA/IndexedDB, Flutter/SQLite, sync idempotente, planes y ML.
- Las pruebas actuales no reemplazan validación E2E contra Railway/Vercel ni pruebas físicas en modo avión.
