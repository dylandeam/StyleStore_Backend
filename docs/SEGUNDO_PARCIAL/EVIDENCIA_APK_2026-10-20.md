# Evidencia de APK — 20 de octubre de 2026

Compilación final ejecutada desde el repositorio `StyleStore_Mobile`, versión
`1.0.3+4`:

```powershell
$env:_JAVA_OPTIONS='-Xmx2048M'
flutter build apk --release --no-tree-shake-icons
```

Resultado verificado:

- Artefacto: `build/app/outputs/flutter-apk/app-release.apk`
- Tamaño: `102932134` bytes (98,2 MB informado por Flutter)
- SHA-256: `72C2B37333E2498B7D1D570E89DFCDAB5D6A646C3EB7A8013C25C7CCEF0747A1`
- Resultado de Gradle: `assembleRelease` aprobado
- `flutter analyze`: sin observaciones
- Pruebas Flutter: `5` aprobadas

Validación física realizada en Samsung Galaxy S21+ (`SM-G996B`), Android 15
(API 35). El APK se actualizó con `adb install -r`: Android conservó la fecha
original de instalación, la sesión y SQLite. Se comprobó arranque sin crash,
cola offline, carga online desde Railway, cierre/reapertura en modo avión,
catálogo recuperado desde SQLite con advertencia de stock provisional y regreso
a conectividad normal.

Durante la prueba se corrigió el host móvil histórico que devolvía HTTP 404 y
se estableció `web-production-07e73.up.railway.app` como API principal. La
cuenta disponible pertenece a un tenant sin productos; reserva/venta offline y
su sincronización comercial real permanecen pendientes de datos y cuenta staff.
