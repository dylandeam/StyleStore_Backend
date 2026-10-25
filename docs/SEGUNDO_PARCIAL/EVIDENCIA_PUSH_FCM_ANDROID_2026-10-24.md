# Evidencia FCM en Android físico — REQ-029

Fecha de cierre: **24/10/2026**  
Dispositivo: **Samsung SM-G996B, Android 15**  
Aplicación: `com.stylestore.stylestore_mobile`

## Resultado

La recepción push quedó comprobada en los tres estados exigidos:

1. **Primer plano:** el endpoint autenticado `POST /api/v1/notificaciones/prueba-push`
   respondió correctamente y Flutter publicó la alerta local mediante el listener FCM.
2. **Segundo plano:** al enviar la prueba y volver al inicio de Android, la barra mostró
   `StyleStore está conectado` con el texto de confirmación del dispositivo.
3. **Aplicación cerrada:** se terminó el proceso de la aplicación sin usar `force-stop`, se
   verificó que `pidof com.stylestore.stylestore_mobile` no devolviera PID y se ejecutó el envío
   desde el contenedor Railway. El servicio devolvió `SENT=1`; Android recibió un mensaje FCM
   nuevo con título `Prueba app cerrada` y texto
   `StyleStore avisa aunque la aplicación esté cerrada.` sin abrir la actividad de StyleStore.

La distinción es importante: no se utilizó `am force-stop`, porque Android bloquea por diseño
la entrega FCM a aplicaciones forzadamente detenidas hasta que el usuario vuelve a abrirlas.
El escenario comprobado equivale al cierre normal desde recientes o a un proceso recuperado por
el sistema.

## Evidencia técnica observada

- Envío remoto: `SENT=1`.
- Clave Android del mensaje cerrado:
  `0|com.stylestore.stylestore_mobile|0|FCM-Notification:253240497|10355`.
- Canal: `stylestore_alerts`, prioridad alta.
- Captura local de la barra: `tmp/samsung-push-closed-remote.png` en la carpeta raíz de trabajo.
- La clave SSH temporal creada exclusivamente para ejecutar la comprobación fue retirada de la
  cuenta Railway y borrada del equipo al terminar.

Con esta evidencia, `REQ-029` pasa de `EN_PRUEBAS` a `TERMINADO_VERIFICADO`.
