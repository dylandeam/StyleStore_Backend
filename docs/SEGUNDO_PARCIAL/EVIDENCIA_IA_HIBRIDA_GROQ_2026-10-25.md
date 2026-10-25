# Evidencia de IA híbrida Groq + motor local — 25/10/2026

## Configuración desplegada

- `GROQ_API_KEY` está guardada como variable protegida en el servicio Backend de Railway.
- El valor no fue leído, impreso, documentado ni versionado.
- Modelo configurado: `openai/gpt-oss-120b`.
- Deployment verificado: `98ef9ffd-6ca1-4f27-840b-3ffd1d2e3baa`, estado `Online`.

## Prueba real online

`GET /api/v1/chatbot/estado` devolvió:

- `modo_preferido=online_groq`;
- `groq_configurado=true`;
- `fallback=reglas_locales`.

Una consulta real a `POST /api/v1/chatbot/mensaje` respondió correctamente con:

- `modo_ia=online_groq`;
- `proveedor_ia=groq`;
- `ia_powered=true`;
- respuesta contextual sobre catálogo, reservas, delivery, pagos y devoluciones.

## Prueba del fallback

La regresión `test_chatbot_uses_local_fallback_when_groq_is_unavailable` simula una clave
configurada cuyo proveedor no responde. El endpoint conserva HTTP 200 y cambia honestamente a:

- `modo_ia=online_local`;
- `proveedor_ia=reglas_locales`;
- `ia_powered=false`.

El motor local mantuvo una respuesta funcional sobre métodos de pago. Así, una caída de Groq
no inutiliza el chatbot ni presenta contenido generado como si proviniera del proveedor externo.

Validación final: 23 pruebas focalizadas y 132 pruebas de la suite backend completa aprobadas.
