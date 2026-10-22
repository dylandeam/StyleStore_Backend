# Evidencia de Calificaciones, Reclamos y Favoritos Multi-Tenant (REQ-064 y REQ-065)

**Fecha**: 2026-10-22  
**Requisitos**:
- `REQ-064` — Calificaciones y reclamos poscompra implementados por tenant con notificación automática al entregar, seguimiento en Web/Móvil y conservación inmutable de nota baja.
- `REQ-065` — Favoritos por usuario y tenant implementados en API, catálogo Web y móvil con aislamiento multi-tenant estricto.  
**Estado resultante**: `TERMINADO_VERIFICADO`

---

## 1. Experiencia Poscompra: Calificaciones y Reclamos (REQ-064)

1. **Notificación Automática Idempotente**:
   - Al marcar una entrega completada (`PATCH /api/v1/envios/{id}/completar`), el backend genera exactamente **una** notificación in-app de tipo `experiencia_poscompra` con enlace directo a `/cuenta/experiencia?orden_id={id}`.
   - Reintentos de completar la entrega son idempotentes y no duplican notificaciones.

2. **Calificación y Regla de Nota Baja**:
   - `POST /api/v1/experiencia/calificaciones`: Recibe `orden_venta_id`, `puntuacion` (1 a 5 estrellas) y `comentario`.
   - Si la puntuación es baja (≤ 2 estrellas), la respuesta incluye `sugerir_reclamo: true`.
   - La nota baja persiste de manera inmutable en base de datos aunque el cliente cancele o decida no registrar un reclamo en ese momento.

3. **Reclamos y Auditoría Administrativa**:
   - `POST /api/v1/experiencia/reclamos`: Permite vincular el reclamo a la calificación y a la sucursal del incidente.
   - El personal y administradores supervisan y actualizan el estado del reclamo (`recibido`, `en_revision`, `resuelto`, `rechazado`) con respuesta oficial mediante `PATCH /api/v1/experiencia/reclamos/{id}`.

4. **Interfaces de Usuario**:
   - Web: Pantalla de experiencia en `web/src/app/features/cuenta/experiencia/` y gestión administrativa en layout.
   - Mobile: Pantalla de experiencia en `mobile/lib/screens/account/experience_screen.dart` con selector de estrellas, textarea y seguimiento.

---

## 2. Favoritos Multi-Tenant (REQ-065)

1. **API de Favoritos (`app/api/v1/favoritos.py`)**:
   - `POST /api/v1/favoritos/{producto_codigo}`: Marca un producto como favorito para el usuario autenticado en su tenant. Idempotente.
   - `DELETE /api/v1/favoritos/{producto_codigo}`: Quita la marca de favorito.
   - `GET /api/v1/favoritos`: Lista los productos favoritos del usuario.
   - **Aislamiento Multi-Tenant**: Si un usuario intenta marcar o consultar un producto que pertenece a otro tenant, la API responde HTTP 404 Not Found protegiendo la frontera de datos.

2. **Consumo en Catálogo**:
   - `GET /api/v1/catalogo`: Los productos retornan la bandera booleana `es_favorito` precalculada según el usuario conectado.
   - Web: Botón de corazón reactivo en tarjetas de producto de `catalogo-list.component.html`.
   - Mobile: Icono de favorito reactivo en `catalog_screen.dart` conectado a `CatalogService.toggleFavorite()`.

---

## 3. Pruebas Automatizadas

En `backend/tests/test_v6_features.py`:
- `test_favorites_are_idempotent_and_exposed_in_catalog`: Añade a favoritos, valida persistencia, consulta catálogo y elimina.
- `test_favorites_reject_products_from_another_tenant`: Intento de acceder a producto ajeno responde HTTP 404.
- `test_low_rating_persists_without_claim_and_can_create_one_later`: Calificación con nota 2 persiste, sugiere reclamo y permite registrarlo con respuesta administrativa.
- `test_delivery_completion_notifies_once_with_experience_link`: Compleción de envío crea notificación única sin duplicados.

---

## 4. Estado de Validación

- Backend: **106 tests pasados**, 0 advertencias de código.
- Web: `ng build` completado con 0 errores y 0 advertencias.
- Mobile: `flutter analyze` 0 issues, `flutter test` 9 pasados.
