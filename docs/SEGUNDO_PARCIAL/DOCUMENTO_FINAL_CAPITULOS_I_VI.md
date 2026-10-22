# Documento Final del Proyecto StyleStore SaaS (Capítulos I a VI)

**Proyecto:** Ecosistema de Comercio Electrónico Multi-empresa (SaaS), Operación Offline (PWA/Mobile) y Analítica Predictiva — StyleStore  
**Materia:** Sistemas de Información II / Ingeniería de Software  
**Fecha de Consolidación:** 21 de Octubre de 2026  
**Requisito Matriz:** `REQ-050 [P1]`  

---

# Índice General

- [Capítulo I: Marco Referencial y Fundamentos del Proyecto](#capítulo-i-marco-referencial-y-fundamentos-del-proyecto)
- [Capítulo II: Modelado y Especificación de Requisitos](#capítulo-ii-modelado-y-especificación-de-requisitos)
- [Capítulo III: Análisis Preliminar y de Robustez (ICONIX)](#capítulo-iii-análisis-preliminar-y-de-robustez-iconix)
- [Capítulo IV: Diseño Detallado del Sistema (UML 2.5+)](#capítulo-iv-diseño-detallado-del-sistema-uml-25)
- [Capítulo V: Arquitectura, Implementación y Tecnologías](#capítulo-v-arquitectura-implementación-y-tecnologías)
- [Capítulo VI: Aseguramiento de Calidad, Pruebas y Resultados](#capítulo-vi-aseguramiento-de-calidad-pruebas-y-resultados)
- [Bibliografía y Fuentes](#bibliografía-y-fuentes)
- [Anexos: Repositorios, Despliegues y Credenciales de Prueba](#anexos)

---

# Capítulo I: Marco Referencial y Fundamentos del Proyecto

## 1.1. Introducción y Antecedentes
El sector minorista de moda y confección enfrenta una transformación continua hacia modelos omnicanal donde convergen tiendas físicas, plataformas web y aplicaciones móviles. Sin embargo, los negocios medianos y las cadenas comerciales en crecimiento sufren importantes barreras tecnológicas:
1. Dependencia de plataformas de comercio electrónico monolíticas y costosas que no admiten una gestión multi-sucursal aislada.
2. Interrupciones operativas y pérdidas de ventas cuando la conectividad a Internet falla en los puntos de venta (POS) físicos.
3. Carencia de herramientas accesibles de inteligencia artificial y predicción de demanda para anticipar quiebres de inventario.

El proyecto **StyleStore** nace como una solución integral que evoluciona el prototipo inicial monousuario hacia una plataforma **Software as a Service (SaaS) Multi-empresa (Multi-tenant)**, permitiendo que múltiples marcas operen de forma autónoma con catálogos personalizados, sucursales físicas, sincronización offline transaccional y asistentes predictivos integrados.

## 1.2. Planteamiento del Problema
¿Cómo diseñar e implementar una arquitectura de software desacoplada, multi-tenant y tolerante a fallos de conectividad que garantice la consistencia del inventario, la seguridad en pagos electrónicos/presenciales y la toma de decisiones mediante analítica de datos en tiendas de moda?

## 1.3. Objetivos del Proyecto

### 1.3.1. Objetivo General
Desarrollar y validar una plataforma de comercio electrónico multi-tenant bajo la metodología **ICONIX**, integrando un backend en FastAPI, un cliente web progresivo (PWA) en Angular 21, una aplicación móvil en Flutter con persistencia SQLite y módulos de Machine Learning deterministas.

### 1.3.2. Objetivos Específicos
1. Implementar un modelo de datos multi-tenant en PostgreSQL con aislamiento lógico estricto por `empresa_id` en todas las entidades de negocio.
2. Diseñar un contrato de sincronización idempotente basado en UUID v4 para la gestión de ventas y reservas offline con detección de conflictos y reembolsos.
3. Desarrollar tres esquemas de suscripción SaaS (Básico, Intermedio y Profesional) con límites operativos y acceso granular a capacidades avanzadas.
4. Construir un motor de reportes interactivo con gráficos SVG nativos, comparativa de sucursales y exportaciones a Excel/PDF.
5. Integrar modelos reproducibles de regresión lineal (Ridge) y clustering (K-Means) sobre métricas de ventas y comportamiento de clientes.
6. Aplicar un riguroso marco de aseguramiento de calidad con una suite automatizada superior a 90 pruebas unitarias y de integración.

## 1.4. Metodología de Desarrollo: ICONIX Process
Para el ciclo de vida del software se adoptó la metodología **ICONIX**, la cual ofrece un equilibrio óptimo entre el Proceso Unificado (PUDS) y el desarrollo ágil extremo (XP). ICONIX se enfoca en el núcleo del análisis y diseño mediante cuatro hitos fundamentales:
- **Análisis de Requisitos y Modelado de Dominio:** Definición de conceptos de negocio y casos de uso en lenguaje del usuario.
- **Análisis de Robustez:** Vinculación de los casos de uso con objetos de frontera (*Boundary*), control (*Control*) y entidad (*Entity*).
- **Diseño Preliminar y Detallado:** Elaboración de diagramas de secuencia UML 2.5+ y diagramas de clases con asignación de métodos.
- **Implementación y Pruebas Unitarias:** Codificación iterativa guiada por pruebas automatizadas y despliegues continuos.

---

# Capítulo II: Modelado y Especificación de Requisitos

## 2.1. Actores del Sistema
- **Administrador SaaS:** Usuario global de la plataforma encargado del alta de empresas, supervisión de planes y respaldos maestros.
- **Administrador Tenant:** Administrador de una marca/empresa específica; gestiona sucursales, empleados, catálogo y finanzas.
- **Encargado de Sucursal:** Supervisa el stock físico local, pedidos con recojo en tienda y traspasos de inventario.
- **Cajero POS:** Operador del punto de venta en mostrador; emite ventas al contado/QR, procesa devoluciones y sincroniza colas offline.
- **Cliente:** Usuario comprador que navega catálogos, guarda prendas favoritas, compra en línea, califica el servicio y gestiona su saldo a favor.
- **Pasarela Externa (PayPal Sandbox API):** Proveedor externo que procesa capturas de órdenes de pago seguras.

## 2.2. Requisitos Funcionales Principales (RF)
- **RF-01 (Multi-tenancy):** El sistema debe aislar los datos entre empresas; ningún usuario de un tenant puede acceder a información de otro.
- **RF-02 (Planes y Suscripciones):** Soporte de tres planes (Básico: hasta 2 sucursales; Intermedio: hasta 5 sucursales + Chatbot; Profesional: 10+ sucursales + Chatbot + Predicciones ML).
- **RF-03 (Variantes y Precios por Talla):** Cada prenda admite tallas y colores diferenciados, con precios configurables por talla y especificación de medidas.
- **RF-04 (Venta y Reserva Offline):** La PWA (Angular) y la app móvil (Flutter) deben permitir registrar ventas de contado y reservas sin red, almacenándolas localmente con UUID v4.
- **RF-05 (Sincronización e Idempotencia):** Al recuperar conexión, las operaciones locales se envían al backend; reintentos con el mismo UUID no duplican registros.
- **RF-06 (Resolución de Conflictos y Reembolsos):** Si al sincronizar una venta offline no hay stock disponible, el sistema marca conflicto y genera un reembolso auditable.
- **RF-07 (Pagos y Notificaciones):** Pagos online vía PayPal Sandbox v2 y QR presencial; cada pago confirmado emite un único correo y notificación.
- **RF-08 (Cambios y Devoluciones):** Plazo configurable (1 a 90 días); cálculo automático de diferencias monetarias y registro de saldo a favor del cliente.
- **RF-09 (Reportes y Comparativa):** Generación de comparativas de rendimiento entre sucursales y exportación a formatos Excel y PDF.
- **RF-10 (Analítica ML):** Predicción de ingresos futuros y segmentación de clientes mediante algoritmos reproducibles.

## 2.3. Requisitos No Funcionales (RNF01–RNF12)
Verificados en su totalidad según `EVIDENCIA_RNF01_RNF12.md`:
- **RNF01 (Seguridad y RBAC):** JWT (30m access, 7d refresh), blacklist de revocación y control de acceso basado en roles.
- **RNF02 (Aislamiento Multi-tenant):** Discriminador `empresa_id` indexado y validado en backend para todos los endpoints.
- **RNF03 (Persistencia Offline):** IndexedDB en PWA y SQLite en Flutter.
- **RNF04 (Integridad Transaccional):** Transacciones ACID con `SELECT ... FOR UPDATE` para descontar stock sin sobreventas.
- **RNF05 (Idempotencia Operativa):** Clave única `operacion_uuid` en `/sync`.
- **RNF06 (Tolerancia y Recuperación):** Manejo inmutable de rechazos con nota de crédito.
- **RNF07 (Mantenibilidad de Esquemas):** 14 migraciones Alembic aditivas con cabeza única `2d4e6f809123`.
- **RNF08 (Interoperabilidad):** REST JSON estándar y fallback multi-host dinámico en móvil.
- **RNF09 (Rendimiento):** Respuesta de endpoints < 100 ms y algoritmos ML en Python puro < 20 ms.
- **RNF10 (Observabilidad y Auditoría):** Bitácora global inmutable de acciones administrativas.
- **RNF11 (Verificabilidad Automatizada):** 97 pruebas backend aprobadas en pytest y 5 pruebas en Flutter.
- **RNF12 (Estándar de Diseño):** Paleta Beige & Navy (`#14263D`, `#CCA77A`) con microanimaciones y gráficos SVG.

---

# Capítulo III: Análisis Preliminar y de Robustez (ICONIX)

## 3.1. Modelado de Dominio
El modelo conceptual organiza las entidades en tres núcleos fundamentales:
1. **Núcleo SaaS / Plataforma:** `Empresa`, `PlanSuscripcion`, `Contratacion`, `Sucursal`, `Usuario`.
2. **Núcleo de Catálogo e Inventario:** `Producto`, `VariantePrenda`, `StockInventario`, `TraspasoInventario`.
3. **Núcleo Transaccional y Auditoría:** `OrdenVenta`, `DetalleVenta`, `Pago`, `OperacionSync`, `CambioDevolucion`, `Bitacora`.

## 3.2. Diagramas de Robustez de Procesos Críticos

### Flujo 1: Sincronización Offline y Resolución de Conflictos
- **Boundary:** Pantalla POS Móvil / Web, Endpoint `POST /api/v1/sync`, Modal de Conflicto.
- **Control:** `OfflineStorageHandler`, `SyncService.procesar_operacion`, `StockService.descontar_con_bloqueo`, `CambioService.crear_reembolso_pendiente`.
- **Entity:** `OperacionSync`, `StockInventario`, `OrdenVenta`, `ReembolsoPendiente`.

### Flujo 2: Comparativa de Sucursales y Consulta de Reportes (REQ-063)
- **Boundary:** Vista Admin Reportes (Web), Endpoint `GET /reportes/comparativa-sucursales/preview`, Descarga PDF/Excel.
- **Control:** `_validate_report_sucursal`, `ReportService.get_comparativa_sucursales_data`, `ReportService.generate_comparativa_pdf`.
- **Entity:** `CurrentUser`, `Sucursal`, `OrdenVenta`, `StockInventario`.

---

# Capítulo IV: Diseño Detallado del Sistema (UML 2.5+)

## 4.1. Diagrama de Secuencia: Checkout y Captura PayPal Sandbox v2
1. Cliente confirma carrito en Web/Móvil con dirección de entrega.
2. `CarritoService` invoca `POST /carrito/checkout` creando la orden en estado `pendiente_pago` y reservando stock con bloqueo transaccional.
3. Se invoca el SDK PayPal abriendo la ventana de aprobación Sandbox.
4. El comprador autoriza la transacción con sus credenciales de prueba.
5. El cliente llama a `POST /pagos/paypal/capturar-orden` pasando el `order_id` de PayPal.
6. `PagoService` captura los fondos vía API REST v2, actualiza la orden a `pagado`, genera el número de recibo, emite la notificación in-app y despacha el correo electrónico de confirmación.

## 4.2. Diseño de Base de Datos y Diccionario de Datos Relacional
La base de datos relacional PostgreSQL consta de 52 tablas administradas por Alembic. Las tablas clave incluyen:
- `empresas`: `id` (UUID PK), `nombre`, `ruc_nit`, `active` (Boolean), `fecha_registro`.
- `planes`: `id` (Int PK), `codigo`, `nombre`, `limite_sucursales`, `capacidades` (JSONB).
- `contrataciones`: `id` (UUID PK), `empresa_id` (FK), `plan_id` (FK), `fecha_vencimiento`, `estado`.
- `stock_inventario`: `id` (UUID PK), `empresa_id` (FK), `sucursal_id` (FK), `variante_id` (FK), `cantidad_disponible` (Int, CHECK >= 0).
- `operaciones_sync`: `operacion_uuid` (UUID PK), `empresa_id` (FK), `tipo_operacion`, `estado`, `payload_solicitud` (JSONB), `payload_resultado` (JSONB).

---

# Capítulo V: Arquitectura, Implementación y Tecnologías

## 5.1. Arquitectura de Despliegue en la Nube
- **Backend API:** FastAPI desplegado sobre la plataforma **Railway** (PaaS) con servidor ASGI Uvicorn y base de datos PostgreSQL 18 gestionada.
- **Frontend Web:** Angular 21 compilado como Progressive Web App (PWA) y distribuido globalmente mediante la red de borde (Edge CDN) de **Vercel**.
- **Cliente Móvil:** Aplicación Flutter compilada en APK Release nativo (`app-release.apk`) con motor de persistencia local SQLite.

## 5.2. Componentes de Inteligencia Artificial y Machine Learning
1. **Regresión Ridge Supervisada:** Modelo matemático determinista implementado en Python puro sobre ventas históricas sintéticas (730 días) para pronosticar ingresos diarios ($R^2 = 0.8913$, $MAE = 28.53$ Bs.).
2. **Segmentación K-Means No Supervisada:** Clasificación de clientes según métricas RFM (Recencia, Frecuencia, Monto) en 3 perfiles estratégicos: Ocasional, Frecuente y Alto Valor.
3. **Vestidor Virtual AR:** Interfaz de prueba asistida con captura de puntos corporales mediante MediaPipe Pose y superposición adaptativa de prendas.

---

# Capítulo VI: Aseguramiento de Calidad, Pruebas y Resultados

## 6.1. Plan y Estrategia de Pruebas
Se implementó una estrategia piramidal con pruebas unitarias de servicios, pruebas de integración de endpoints protegidos y pruebas end-to-end (E2E) de flujos comerciales:
- **Suite Backend:** 97 pruebas automatizadas ejecutadas con `pytest -q`:
  - Aislamiento multi-tenant A/B (100% aprobado).
  - Rechazo 404 a sondas de sucursales ajenas (100% aprobado).
  - Idempotencia en confirmación de pagos y deduplicación de correo (100% aprobado).
  - Detección de sobreventa y reembolso de órdenes sync (100% aprobado).
  - Modelos predictivos ML y filtros por capacidad de plan (100% aprobado).
- **Suite Mobile:** 5 pruebas unitarias en Flutter aprobadas y análisis estático con 0 incidencias (`flutter analyze --no-pub`).
- **Compilación Web:** `npm.cmd run build` generando bundle de producción `main-S46ZNSZX.js` con 0 errores.

## 6.2. Conclusiones y Recomendaciones
1. **Conclusión:** Se completó con éxito la transformación del ecosistema StyleStore en una solución SaaS robusta, cumpliendo con los estándares de ingeniería de software, arquitectura multi-tenant y tolerancia a desconexión requeridos para la defensa del segundo parcial.
2. **Recomendación Operativa:** Para el pase a producción comercial definitiva, se sugiere reanudar el ciclo de despliegue en Railway aplicando la migración `2d4e6f809123` y sustituir las credenciales de prueba por un gestor de secretos en la nube.

---

# Bibliografía y Fuentes

1. Rosenberg, D., & Scott, K. (2001). *Applying Use Case Driven Object Modeling with UML: An Annotated E-Commerce Example*. Addison-Wesley.
2. Object Management Group (OMG). (2015). *OMG Unified Modeling Language (OMG UML), Version 2.5*.
3. Fowler, M. (2002). *Patterns of Enterprise Application Architecture*. Addison-Wesley.
4. FastAPI Documentation. (2024). *Advanced User Guide & Dependency Injection*. Tiangolo.
5. Google Developers. (2024). *Progressive Web Apps Overview & Service Workers API*.

---

# Anexos

## A. Repositorios Oficiales en GitHub
- **Backend:** `https://github.com/dylandeam/StyleStore_Backend.git` (Rama `main`)
- **Frontend Web:** `https://github.com/dylandeam/StyleStore_Frontend.git` (Rama `main`)
- **Mobile App:** `https://github.com/dylandeam/StyleStore_Mobile.git` (Rama `main`)

## B. Enlaces Públicos de Despliegue
- **Web en Producción (Vercel):** `https://style-store-frontend-nine.vercel.app` (Sirviendo bundle `main-S46ZNSZX.js`)
- **Backend en Producción (Railway):** `https://web-production-07e73.up.railway.app`
- **Documentación Swagger / OpenAPI:** `https://web-production-07e73.up.railway.app/docs`

## C. Credenciales Demostrativas (Entorno Sandbox)
- **Administrador SaaS Global:** `admin@stylestore.com` / `admin123`
- **Comprador PayPal Sandbox:** `comprador.sandbox@stylestore.com` / `SandboxPass2026!`
