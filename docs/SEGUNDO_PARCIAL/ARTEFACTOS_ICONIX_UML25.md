# Artefactos de Modelado ICONIX y UML 2.5+ — StyleStore SaaS (Segundo Parcial)

Fecha: 21/10/2026.  
Metodología: **ICONIX Process** (Rosenberg & Scott) adaptado para arquitectura Cloud Multi-tenant y PWA/Mobile Offline.  
Estándar de notación: **UML 2.5+** estructurado mediante diagramas Mermaid y especificación de flujos.  
Requisito matriz: `REQ-049 [P1]`.

---

## 1. Introducción y Metodología ICONIX

La metodología ICONIX es un enfoque ágil y estructurado entre el modelado exhaustivo del Proceso Unificado (PUDS) y el desarrollo rápido. Se compone de 4 fases iterativas:
1. **Modelado de Requisitos y Dominio:** Identificación de actores, glosario del dominio y diagrama de casos de uso.
2. **Análisis y Diseño Preliminar (Robustez):** Nexo entre el análisis ("qué") y el diseño ("cómo"), empleando los tres estereotipos:
   - **Boundary (Frontera/Límite):** Pantallas Web (Angular PWA), Vistas Mobile (Flutter) y Endpoints API REST (FastAPI).
   - **Control (Controlador/Servicio):** Capa de servicios (`AuthService`, `SyncService`, `ReportService`, `PagoService`, `CambioService`).
   - **Entity (Entidad):** Modelos de datos persistentes en PostgreSQL / SQLite.
3. **Diseño Detallado (Secuencia y Clases):** Asignación de responsabilidades a clases y mensajes síncronos/asíncronos.
4. **Implementación y Verificación:** Código fuente, migraciones Alembic y pruebas unitarias/E2E.

---

## 2. Modelo de Dominio del Negocio (Domain Model)

El modelo de dominio representa las entidades conceptuales del sistema SaaS multi-empresa, sus atributos esenciales y las relaciones de agregación y composición.

```mermaid
classDiagram
    direction TB

    class Empresa {
        +UUID id
        +String nombre
        +String ruc_nit
        +String subdominio
        +Boolean active
        +DateTime fecha_registro
    }

    class PlanSuscripcion {
        +Integer id
        +String codigo
        +String nombre
        +Decimal precio_mensual
        +Integer limite_sucursales
        +Boolean tiene_chatbot
        +Boolean tiene_predicciones
        +JSON capacidades
    }

    class Contratacion {
        +UUID id
        +UUID empresa_id
        +Integer plan_id
        +DateTime fecha_inicio
        +DateTime fecha_vencimiento
        +String estado
        +String estado_pago
    }

    class Sucursal {
        +UUID id
        +UUID empresa_id
        +String nombre
        +String direccion
        +String ciudad
        +Decimal latitud
        +Decimal longitud
        +String horario_apertura
        +String horario_cierre
    }

    class Usuario {
        +UUID id
        +UUID empresa_id
        +String email
        +String hashed_password
        +String rol
        +Boolean is_platform_admin
        +Boolean activo
    }

    class Empleado {
        +String codigo
        +UUID user_id
        +UUID empresa_id
        +UUID sucursal_id
        +String jornada
        +String cargo
    }

    class Cliente {
        +String codigo
        +UUID user_id
        +UUID empresa_id
        +String ci_nit
        +String telefono
        +Decimal saldo_a_favor
    }

    class Producto {
        +String codigo
        +UUID empresa_id
        +String nombre
        +String descripcion
        +Decimal precio_base
        +String categoria
        +String foto_url
    }

    class VariantePrenda {
        +UUID id
        +String producto_codigo
        +String talla
        +String color
        +Decimal precio_efectivo
        +JSON medidas
    }

    class StockInventario {
        +UUID id
        +UUID variante_id
        +UUID sucursal_id
        +UUID empresa_id
        +Integer cantidad_disponible
        +Integer stock_minimo
    }

    class OrdenVenta {
        +UUID id
        +UUID empresa_id
        +UUID sucursal_id
        +String cliente_codigo
        +String tipo_canal
        +String tipo_entrega
        +Decimal subtotal
        +Decimal costo_delivery
        +Decimal descuento
        +Decimal total
        +String estado_orden
        +DateTime fecha_hora
    }

    class DetalleVenta {
        +UUID id
        +UUID orden_id
        +UUID variante_id
        +Integer cantidad
        +Decimal precio_unitario
        +Decimal total_linea
    }

    class Pago {
        +UUID id
        +UUID empresa_id
        +UUID orden_id
        +String metodo_pago
        +Decimal monto
        +String estado_pago
        +String transaccion_ref
        +String recibo_numero
        +Boolean correo_confirmado
    }

    class OperacionSync {
        +UUID operacion_uuid
        +UUID empresa_id
        +UUID sucursal_id
        +UUID usuario_id
        +String tipo_operacion
        +String estado
        +String motivo_rechazo
        +JSON payload_solicitud
        +JSON payload_resultado
        +DateTime fecha_sincronizacion
    }

    Empresa "1" *-- "1..*" Sucursal : posee
    Empresa "1" *-- "1..*" Contratacion : contrata
    PlanSuscripcion "1" <-- "0..*" Contratacion : basado en
    Empresa "1" *-- "1..*" Usuario : agrupa
    Usuario "1" <-- "0..1" Empleado : perfil empleado
    Usuario "1" <-- "0..1" Cliente : perfil cliente
    Empresa "1" *-- "1..*" Producto : administra
    Producto "1" *-- "1..*" VariantePrenda : tiene variantes
    VariantePrenda "1" *-- "0..*" StockInventario : distribuido en
    Sucursal "1" *-- "0..*" StockInventario : almacena
    Empresa "1" *-- "0..*" OrdenVenta : registra
    OrdenVenta "1" *-- "1..*" DetalleVenta : contiene
    OrdenVenta "1" *-- "1" Pago : cancelado con
    Empresa "1" *-- "0..*" OperacionSync : audita
```

---

## 3. Modelo de Casos de Uso (Use Case Model)

### 3.1. Actores del Sistema
1. **Administrador SaaS:** Administrador supremo de la plataforma; gestiona contratos, empresas/tenants, catálogo de planes y respaldos globales.
2. **Administrador Tenant:** Responsable de una tienda o marca específica; administra sucursales, empleados, catálogo propio, inventario, reportes de empresa y renovación del plan.
3. **Encargado de Sucursal:** Supervisa el stock físico, transferencias entre tiendas y agenda de retiros/reservas en su sucursal.
4. **Cajero POS:** Registra ventas al contado o por QR en mostrador, procesa devoluciones/cambios y sincroniza colas offline.
5. **Cliente:** Navega el catálogo multitenant, guarda favoritos, realiza compras online o reservas, califica el servicio y gestiona su saldo a favor.
6. **Pasarela de Pagos (PayPal Sandbox):** Servicio externo que procesa autorizaciones y capturas de compras electrónicas seguras.

### 3.2. Diagrama General de Casos de Uso

```mermaid
graph LR
    actorSaaS["👤 Administrador SaaS"]
    actorAdmin["👤 Administrador Tenant"]
    actorCajero["👤 Cajero POS"]
    actorCliente["👤 Cliente"]
    pasarela["🌐 PayPal Sandbox API"]

    subgraph "Módulo 1: Plataforma & Suscripciones SaaS"
        CU01["CU-01: Gestionar Empresas / Tenants"]
        CU02["CU-02: Configurar Planes y Capacidades"]
        CU03["CU-03: Renovar / Cambiar Plan de Empresa"]
    end

    subgraph "Módulo 2: Operaciones Comerciales & POS"
        CU04["CU-04: Registrar Venta Presencial (Caja POS)"]
        CU05["CU-05: Realizar Checkout Online"]
        CU06["CU-06: Procesar Pago Electrónico"]
        CU07["CU-07: Sincronizar Ventas/Reservas Offline"]
    end

    subgraph "Módulo 3: Post-Venta & Fidelización"
        CU08["CU-08: Procesar Cambio o Devolución"]
        CU09["CU-09: Gestionar Reservas con Franja Horaria"]
        CU10["CU-10: Calificar Experiencia Poscompra"]
    end

    subgraph "Módulo 4: Analítica & Business Intelligence"
        CU11["CU-11: Comparar Rendimiento entre Sucursales"]
        CU12["CU-12: Consultar Predicciones ML y Reportes"]
    end

    actorSaaS --> CU01
    actorSaaS --> CU02

    actorAdmin --> CU03
    actorAdmin --> CU11
    actorAdmin --> CU12

    actorCajero --> CU04
    actorCajero --> CU07
    actorCajero --> CU08

    actorCliente --> CU05
    actorCliente --> CU09
    actorCliente --> CU10

    CU05 ..> CU06 : <<include>>
    CU06 --> pasarela
    CU07 ..> CU04 : <<resolves>>
```

---

## 4. Diagramas de Robustez ICONIX (Robustness Analysis)

El análisis de robustez conecta los casos de uso con el diseño de clases identificando objetos de Frontera (Boundary), Control (Control) y Entidad (Entity).

### 4.1. Robustez 1: Venta Presencial Offline y Sincronización con Resolución de Conflicto

```mermaid
graph LR
    subgraph "Boundary (Límites)"
        UI_POS["🖥️ PWA / Mobile POS Screen"]
        API_SYNC["⚡ POST /api/v1/sync"]
        UI_ALERT["⚠️ Modal Aviso Conflicto Stock"]
    end

    subgraph "Control (Controladores & Servicios)"
        CTRL_OFF["⚙️ OfflineQueueHandler"]
        CTRL_SYNC["⚙️ SyncService.procesar_operacion"]
        CTRL_STOCK["⚙️ StockService.descontar_con_bloqueo"]
        CTRL_REFUND["⚙️ CambioService.crear_reembolso_pendiente"]
    end

    subgraph "Entity (Entidades)"
        ENT_QUEUE[("💾 IndexedDB / SQLite Queue")]
        ENT_SYNC[("🐘 OperacionSync")]
        ENT_STOCK[("🐘 StockInventario")]
        ENT_VENTA[("🐘 OrdenVenta")]
        ENT_REFUND[("🐘 ReembolsoPendiente")]
    end

    UI_POS -->|"1: Registrar venta contado sin red"| CTRL_OFF
    CTRL_OFF -->|"2: Guardar con UUID v4"| ENT_QUEUE
    CTRL_OFF -->|"3: Al detectar reconexión"| API_SYNC
    API_SYNC -->|"4: Delegar payload"| CTRL_SYNC
    CTRL_SYNC -->|"5: Validar idempotencia UUID"| ENT_SYNC
    CTRL_SYNC -->|"6: Verificar existencia real"| CTRL_STOCK
    CTRL_STOCK -->|"7: Bloqueo SELECT FOR UPDATE"| ENT_STOCK

    CTRL_STOCK -.->|"8a: Stock suficiente"| ENT_VENTA
    CTRL_STOCK -.->|"8b: Stock insuficiente (Conflicto)"| CTRL_REFUND
    CTRL_REFUND -->|"9: Crear orden reembolso auditable"| ENT_REFUND
    CTRL_SYNC -->|"10: Notificar rechazo con motivo"| UI_ALERT
```

### 4.2. Robustez 2: Comparativa de Rendimiento entre Sucursales (REQ-063)

```mermaid
graph LR
    subgraph "Boundary (Límites)"
        UI_REP["🖥️ Vista Reportes Admin (Web)"]
        API_REP["⚡ GET /reportes/comparativa-sucursales/preview"]
        API_EXP["⚡ GET /reportes/comparativa-sucursales/pdf"]
    end

    subgraph "Control (Controladores & Servicios)"
        DEP_SEC["⚙️ _validate_report_sucursal (Deps)"]
        CTRL_REP["⚙️ ReportService.get_comparativa_sucursales_data"]
        CTRL_PDF["⚙️ ReportService.generate_comparativa_pdf"]
    end

    subgraph "Entity (Entidades)"
        ENT_USR[("🐘 CurrentUser (JWT Tenant)")]
        ENT_SUC[("🐘 Sucursal (Scoped)")]
        ENT_VENTAS[("🐘 OrdenVenta")]
        ENT_STOCK[("🐘 StockInventario")]
    end

    UI_REP -->|"1: Cargar dashboard sucursales"| API_REP
    API_REP -->|"2: Extraer tenant del JWT"| ENT_USR
    API_REP -->|"3: Validar ámbito de empresa"| DEP_SEC
    DEP_SEC -->|"4: Rechazar sondas ajenas (404)"| ENT_SUC
    API_REP -->|"5: Solicitar agregados comparativos"| CTRL_REP
    CTRL_REP -->|"6: Calcular ventas y ticket promedio"| ENT_VENTAS
    CTRL_REP -->|"7: Consolidar stock y criticidad <= 5"| ENT_STOCK
    CTRL_REP -->|"8: Retornar DTO comparativo"| UI_REP
    UI_REP -->|"9: Solicitar descarga PDF"| API_EXP
    API_EXP -->|"10: Renderizar ReportLab bytes"| CTRL_PDF
```

---

## 5. Diagramas de Secuencia UML 2.5+ (Sequence Diagrams)

### 5.1. Secuencia: Sincronización Idempotente con Detección de Conflicto y Generación de Reembolso

```mermaid
sequenceDiagram
    autonumber
    actor Cajero as Cajero POS (Mobile / PWA)
    participant LocalDB as SQLite / IndexedDB
    participant SyncAPI as API /api/v1/sync
    participant SyncService as SyncService
    participant StockService as StockService
    participant DB as PostgreSQL (DB)
    participant MailService as Email / Notification Service

    Note over Cajero, LocalDB: Modo Avión / Sin Conectividad
    Cajero->>LocalDB: registrar_venta_contado(payload)
    LocalDB-->>Cajero: operacion_uuid (UUIDv4) guardado en cola "pendiente"

    Note over Cajero, SyncAPI: Recuperación de Red
    LocalDB->>SyncAPI: POST /sync (operacion_uuid, payload, JWT)
    SyncAPI->>SyncService: procesar_operacion(current_user, operacion_uuid, payload)
    
    SyncService->>DB: SELECT * FROM operaciones_sync WHERE operacion_uuid = :uuid
    alt Operación ya procesada previamente (Replay idempotente)
        DB-->>SyncService: operacion_existente (estado, resultado)
        SyncService-->>SyncAPI: 200 OK (payload_resultado previo en caché)
        SyncAPI-->>LocalDB: Actualizar estado local a "confirmado"
    else Nueva Operación
        SyncService->>DB: BEGIN TRANSACTION
        SyncService->>StockService: descontar_stock(variante_id, sucursal_id, cantidad)
        StockService->>DB: SELECT cantidad_disponible FROM stock_inventario WHERE ... FOR UPDATE
        DB-->>StockService: cantidad_disponible = 0 (Agotado por venta online previa)
        
        alt Stock Agotado (Conflicto de Concurrencia)
            StockService-->>SyncService: Error: StockInsuficienteException
            SyncService->>DB: INSERT INTO cambios_devolucion (reembolso_pendiente, motivo, saldo)
            SyncService->>DB: INSERT INTO operaciones_sync (estado='conflicto', motivo='Prenda no disponible')
            SyncService->>DB: COMMIT TRANSACTION
            SyncService-->>SyncAPI: 200 OK (estado='conflicto', reembolso_id='NCJ-9821')
            SyncAPI-->>LocalDB: Actualizar cola local a 'conflicto'
            LocalDB-->>Cajero: Mostrar alerta modal: "Stock agotado. Cobro registrado como reembolso pendiente."
        else Stock Disponible
            StockService->>DB: UPDATE stock_inventario SET cantidad = cantidad - n
            SyncService->>DB: INSERT INTO orden_venta (...)
            SyncService->>DB: INSERT INTO operaciones_sync (estado='confirmado')
            SyncService->>DB: COMMIT TRANSACTION
            SyncService->>MailService: disparar_recibo_pago(orden_id)
            SyncService-->>SyncAPI: 200 OK (estado='confirmado', orden_id)
            SyncAPI-->>LocalDB: Marcar 'confirmado' en cola local
        end
    end
```

---

## 6. Diagrama de Clases de Diseño (Design Class Diagram - UML 2.5)

```mermaid
classDiagram
    class Base {
        <<SQLAlchemy Declarative>>
    }

    class ReportesRouter {
        <<FastAPI Controller>>
        +get_comparativa_preview(db, current_user, sucursal_id)
        +exportar_comparativa_excel(db, current_user, sucursal_id)
        +exportar_comparativa_pdf(db, current_user, sucursal_id)
        -_validate_report_sucursal(db, current_user, sucursal_id)
    }

    class ReportService {
        <<Domain Service>>
        +get_comparativa_sucursales_data(db, empresa_id, sucursal_id) ComparativaResponse
        +generate_comparativa_excel(data) BytesIO
        +generate_comparativa_pdf(data) BytesIO
    }

    class SyncRouter {
        <<FastAPI Controller>>
        +sincronizar_operacion(req, db, current_user)
        +obtener_estado_operacion(uuid, db, current_user)
    }

    class SyncService {
        <<Domain Service>>
        +procesar_operacion(db, user, uuid, payload) SyncResult
        +resolver_conflicto_stock(db, operacion)
    }

    class PagoService {
        <<Domain Service>>
        +confirmar(db, pago_id, user) PagoConfirmadoResult
        +capturar_paypal(db, order_id, user)
    }

    class BitacoraService {
        <<Cross-Cutting Service>>
        +registrar(db, user_id, empresa_id, modulo, accion, ip, detalle)
    }

    ReportesRouter --> ReportService : delega cálculo
    SyncRouter --> SyncService : procesa cola
    SyncService --> BitacoraService : audita conflicto
    PagoService --> BitacoraService : audita captura
```

---

## 7. Diagrama de Despliegue y Componentes (Deployment & Architecture Diagram)

```mermaid
graph TB
    subgraph "Navegador Web (Cliente PWA)"
        PWA["🌐 Angular 21 Standalone App<br/>(Vercel CDN Edge)"]
        SW["⚙️ Service Worker (ngsw-worker)"]
        IDB[("💾 IndexedDB (stylestore_offline)")]
        PWA --> SW
        SW --> IDB
    end

    subgraph "Dispositivo Móvil Android (Cliente Mobile)"
        APK["📱 Flutter Application (APK 1.0.3+4)"]
        SS["🔐 FlutterSecureStorage (JWT ilimitado)"]
        SQL[("💾 SQLite Database (stylestore.db)")]
        APK --> SS
        APK --> SQL
    end

    subgraph "Servicios Cloud Externos"
        PAYPAL["🌐 PayPal Sandbox REST API v2"]
        SMTP["✉️ Servidor SMTP Transaccional"]
    end

    subgraph "Infraestructura Cloud Backend (Railway PaaS)"
        API_GATEWAY["⚡ FastAPI Gateway / Reverse Proxy (Uvicorn)"]
        
        subgraph "Servicios Internos"
            AUTH_CORE["🔐 Core Auth & Multi-tenant Deps"]
            SYNC_CORE["🔄 Sync & Idempotency Engine"]
            REPORT_CORE["📊 Report & Comparativa Engine"]
            ML_CORE["🧠 ML Predictor (Ridge + K-means)"]
        end

        DB_PROD[("🐘 PostgreSQL 18 Managed DB<br/>(Alembic Head: 2d4e6f809123)")]
    end

    PWA -->|"HTTPS / REST / JSON (JWT)"| API_GATEWAY
    APK -->|"HTTPS / REST / JSON (Dynamic Host Fallback)"| API_GATEWAY

    API_GATEWAY --> AUTH_CORE
    API_GATEWAY --> SYNC_CORE
    API_GATEWAY --> REPORT_CORE
    API_GATEWAY --> ML_CORE

    AUTH_CORE --> DB_PROD
    SYNC_CORE --> DB_PROD
    REPORT_CORE --> DB_PROD
    ML_CORE --> DB_PROD

    API_GATEWAY -->|"OAuth2 Capture"| PAYPAL
    API_GATEWAY -->|"TLS Notification"| SMTP
```

---

## 8. Extensión ICONIX: redistribución predictiva de stock

### 8.1. Caso de uso CU-13 — Revisar y ejecutar recomendación de traspaso

**Actor principal:** Administrador tenant o encargado autorizado.

**Precondiciones:** usuario autenticado, plan con capacidad `predicciones`, dos o más sucursales del mismo tenant y stock comparable de la misma variante.
**Flujo básico:**

1. El actor abre Inventario y solicita actualizar el análisis.
2. El sistema agrupa stock por producto, color y talla dentro del tenant.
3. El sistema calcula velocidad de venta y cobertura de los últimos 30 días.
4. El sistema descuenta entradas/salidas de traspasos pendientes.
5. El sistema propone origen, destino y cantidad conservando la reserva del origen.
6. El actor revisa la explicación, ajusta si corresponde y crea la solicitud.
7. Un usuario autorizado aprueba el traspaso; recién entonces el backend mueve stock atómicamente.

**Flujos alternos:** sin capacidad de plan se responde 403; una sucursal ajena se responde 404; si cambia el stock antes de aprobar, se rechaza con conflicto y no se mueve ninguna unidad; repetir una solicitud con la misma clave idempotente devuelve el mismo traspaso.

### 8.2. Robustez

```mermaid
graph LR
    Admin["Actor: Administrador tenant"] --> UI["Boundary: Inventario Angular"]
    UI --> API["Boundary: Reportes API"]
    API --> ML["Control: MLService.transfer_recommendations"]
    ML --> Ventas["Entity: OrdenVenta / DetalleVenta"]
    ML --> Stock["Entity: StockInventario"]
    ML --> Pendientes["Entity: TraspasoInventario"]
    ML --> API
    API --> UI
    UI --> TransferAPI["Boundary: Inventario / traspasos"]
    TransferAPI --> TransferService["Control: TraspasoInventarioService"]
    TransferService --> Stock
    TransferService --> Pendientes
```

### 8.3. Secuencia de recomendación y aprobación

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Administrador tenant
    participant Web as Inventario Angular
    participant ReportAPI as Reportes API
    participant ML as MLService
    participant DB as PostgreSQL
    participant TransferAPI as Traspasos API

    Admin->>Web: Actualizar análisis
    Web->>ReportAPI: GET recomendaciones-traspaso-stock (JWT)
    ReportAPI->>ReportAPI: validar tenant, sucursal y capacidad
    ReportAPI->>ML: transfer_recommendations(sucursal_id)
    ML->>DB: stock + ventas 30d + traspasos pendientes
    DB-->>ML: datos aislados del tenant
    ML-->>Web: recomendaciones explicadas
    Admin->>Web: Revisar traspaso
    Web->>TransferAPI: POST solicitud (idempotency_key)
    TransferAPI-->>Web: estado pendiente
    Admin->>TransferAPI: Aprobar solicitud
    TransferAPI->>DB: bloquear, revalidar y mover stock atómicamente
    DB-->>TransferAPI: commit
    TransferAPI-->>Web: traspaso aprobado
```

---

## 9. Verificación y Trazabilidad

- **Trazabilidad de Requisitos:** Los artefactos modelados cubren con rigor técnico los requerimientos `REQ-001` a `REQ-074`, en especial el diseño de sincronización offline (`REQ-013`, `REQ-023`–`REQ-036`), multitenancy (`REQ-003`–`REQ-007`), transacciones atómicas (`REQ-011`, `REQ-012`), reportes comparativos (`REQ-039`, `REQ-063`), analítica ML (`REQ-042`–`REQ-045`) y redistribución predictiva (`REQ-074`).
- **Validación:** El modelado se corresponde unívocamente con el código real versionado en los repositorios de GitHub de Backend, Frontend Web y Mobile.
