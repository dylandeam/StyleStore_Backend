# Evidencia de APK — 20 de octubre de 2026

Compilación ejecutada desde el repositorio `StyleStore_Mobile`, rama `main`,
commit `2601c09`:

```powershell
$env:_JAVA_OPTIONS='-Xmx2048M'
flutter build apk --release --no-tree-shake-icons
```

Resultado verificado:

- Artefacto: `build/app/outputs/flutter-apk/app-release.apk`
- Tamaño: `102932130` bytes (98,2 MB informado por Flutter)
- SHA-256: `72A059D045655B3DD837420B88F65D2C55FA75D67C4E4AC57C9B28B20DDF2E56`
- Resultado de Gradle: `assembleRelease` aprobado
- Árbol Git móvil: limpio después de compilar

La detección de dispositivos mostró únicamente Windows, Chrome y Edge. No
había teléfono Android ni emulador Android conectado, por lo que la instalación,
el cierre/reapertura y la prueba integral en modo avión continúan pendientes y
no se consideran verificadas.
