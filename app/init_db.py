"""
Database initialization and default admin / permissions seeder.
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal, Base, engine
from app.config import settings
import app.models  # Registra todos los modelos en Base.metadata
from app.models.user import User
from app.core.security import hash_password
from app.services.role_service import RoleService

logger = logging.getLogger("init_db")


def _run_column_migrations(db: Session):
    """Ejecuta migraciones defensivas para añadir columnas nuevas si no existen."""
    statements = [
        # Users
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS developer_key_hash VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS bitacora_password_hash VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_platform_admin BOOLEAN DEFAULT FALSE",
        "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS inactive_reason VARCHAR(40)",
        "ALTER TABLE contrataciones_plan ADD COLUMN IF NOT EXISTS estado_pago VARCHAR(20) DEFAULT 'pagado'",
        "ALTER TABLE contrataciones_plan ADD COLUMN IF NOT EXISTS referencia_pago VARCHAR(120)",
        "ALTER TABLE contrataciones_plan ADD COLUMN IF NOT EXISTS pagado_en TIMESTAMP WITH TIME ZONE",
        "UPDATE contrataciones_plan SET estado_pago = 'pagado' WHERE estado_pago IS NULL",
        "UPDATE contrataciones_plan SET referencia_pago = 'LEGACY-' || id WHERE estado_pago = 'pagado' AND referencia_pago IS NULL",
        "UPDATE contrataciones_plan SET pagado_en = created_at WHERE estado_pago = 'pagado' AND pagado_en IS NULL",
        # Bitacora
        "ALTER TABLE bitacora ADD COLUMN IF NOT EXISTS ip_address VARCHAR(50)",
        "ALTER TABLE bitacora ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
        # OrdenVenta
        "ALTER TABLE orden_venta ADD COLUMN IF NOT EXISTS carrito_id INTEGER",
        "ALTER TABLE orden_venta ADD COLUMN IF NOT EXISTS ticket_numero VARCHAR(50)",
        "ALTER TABLE orden_venta ADD COLUMN IF NOT EXISTS efectivo_recibido NUMERIC(10, 2)",
        "ALTER TABLE orden_venta ADD COLUMN IF NOT EXISTS cambio_devuelto NUMERIC(10, 2)",
        "ALTER TABLE orden_venta ADD COLUMN IF NOT EXISTS metodo_pago VARCHAR(50)",
        "ALTER TABLE orden_venta ALTER COLUMN sucursal_id DROP NOT NULL",
        # DetalleVenta
        "ALTER TABLE detalle_venta ADD COLUMN IF NOT EXISTS stock_inventario_id INTEGER",
        "ALTER TABLE detalle_venta ADD COLUMN IF NOT EXISTS producto_nombre VARCHAR(150)",
        "ALTER TABLE detalle_venta ADD COLUMN IF NOT EXISTS color_nombre VARCHAR(50)",
        "ALTER TABLE detalle_venta ADD COLUMN IF NOT EXISTS talla_nombre VARCHAR(20)",
        "ALTER TABLE detalle_venta ADD COLUMN IF NOT EXISTS cantidad INTEGER",
        "ALTER TABLE detalle_venta ADD COLUMN IF NOT EXISTS precio_unitario NUMERIC(10, 2)",
        "ALTER TABLE detalle_venta ADD COLUMN IF NOT EXISTS subtotal NUMERIC(10, 2)",
        # Variantes de inventario por talla/color/sucursal
        "ALTER TABLE stock_inventario ADD COLUMN IF NOT EXISTS precio_variante NUMERIC(12, 2)",
        "ALTER TABLE stock_inventario ADD COLUMN IF NOT EXISTS medidas JSON DEFAULT '{}'",
        # Pagos
        "ALTER TABLE pagos ADD COLUMN IF NOT EXISTS paypal_capture_id VARCHAR(100)",
        "ALTER TABLE pagos ADD COLUMN IF NOT EXISTS metodo_pago VARCHAR(50)",
        "ALTER TABLE pagos ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
        "ALTER TABLE pagos ADD COLUMN IF NOT EXISTS recibo_numero VARCHAR(40)",
        "ALTER TABLE pagos ADD COLUMN IF NOT EXISTS email_confirmacion_enviado_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE pagos ADD COLUMN IF NOT EXISTS email_confirmacion_intentos INTEGER DEFAULT 0",
        "ALTER TABLE notificaciones ADD COLUMN IF NOT EXISTS pago_id INTEGER",
        # Clientes
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS foto VARCHAR(255)",
        # Sucursales
        "ALTER TABLE sucursales ADD COLUMN IF NOT EXISTS latitud NUMERIC(10, 6)",
        "ALTER TABLE sucursales ADD COLUMN IF NOT EXISTS longitud NUMERIC(10, 6)",
        "ALTER TABLE sucursales ADD COLUMN IF NOT EXISTS maps_url VARCHAR(500)",
        "ALTER TABLE sucursales ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
        # Catálogo y operaciones por empresa
        "ALTER TABLE categorias ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
        "ALTER TABLE colores ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
        "ALTER TABLE tallas ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
        "ALTER TABLE temporadas ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
        "ALTER TABLE colecciones ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
        "ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
        # Envios v7 (distancia real y repartidor)
        "ALTER TABLE envios ADD COLUMN IF NOT EXISTS token_seguimiento VARCHAR(100)",
        "ALTER TABLE envios ADD COLUMN IF NOT EXISTS tracking_activo BOOLEAN DEFAULT TRUE",
        "ALTER TABLE envios ADD COLUMN IF NOT EXISTS repartidor_id INTEGER",
        "ALTER TABLE envios ADD COLUMN IF NOT EXISTS repartidor_lat NUMERIC(10, 6)",
        "ALTER TABLE envios ADD COLUMN IF NOT EXISTS repartidor_lon NUMERIC(10, 6)",
        "ALTER TABLE envios ADD COLUMN IF NOT EXISTS repartidor_actualizado_en TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE envios ADD COLUMN IF NOT EXISTS latitud_destino NUMERIC(10, 6)",
        "ALTER TABLE envios ADD COLUMN IF NOT EXISTS longitud_destino NUMERIC(10, 6)",
        "ALTER TABLE envios ADD COLUMN IF NOT EXISTS distancia_km NUMERIC(8, 2)",
        "ALTER TABLE envios ADD COLUMN IF NOT EXISTS minutos_estimados INTEGER",
        "ALTER TABLE envios ADD COLUMN IF NOT EXISTS yango_tracking_code VARCHAR(100)",
        "ALTER TABLE envios ADD COLUMN IF NOT EXISTS yango_tracking_url VARCHAR(500)",
        "ALTER TABLE envios ADD COLUMN IF NOT EXISTS delivery_conductor VARCHAR(150)",
        "ALTER TABLE envios ADD COLUMN IF NOT EXISTS ubicacion_url VARCHAR(500)",
        # Backup Logs
        "ALTER TABLE backup_logs ADD COLUMN IF NOT EXISTS contenido_json TEXT",
        # Categorías (Vestidor Virtual RA - v8)
        "ALTER TABLE categorias ADD COLUMN IF NOT EXISTS tipo_ar VARCHAR(30) DEFAULT 'superior'",
        # Productos (Vestidor Virtual, Fotos y Promociones)
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS foto_trasera VARCHAR(255)",
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS foto_vestidor_frontal VARCHAR(255)",
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS foto_vestidor_trasera VARCHAR(255)",
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS tipo_prenda VARCHAR(30) DEFAULT 'superior'",
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS puntos_clave_ia TEXT",
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS en_promocion BOOLEAN DEFAULT FALSE",
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS porcentaje_descuento INTEGER DEFAULT 0",
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS precio_descuento NUMERIC(10, 2)",
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS titulo_promocion VARCHAR(100)",
        # Producto Landmarks (v8)
        """
        CREATE TABLE IF NOT EXISTS producto_landmarks (
            producto_codigo VARCHAR(50) PRIMARY KEY,
            tipo_ar VARCHAR(30) NOT NULL DEFAULT 'superior',
            landmarks JSON NOT NULL,
            calibrado_por INTEGER,
            calibrado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Pruebas Virtuales (v8)
        """
        CREATE TABLE IF NOT EXISTS pruebas_virtuales (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            producto_codigo VARCHAR(50) NOT NULL,
            foto_persona_url VARCHAR(500) NOT NULL,
            foto_resultado_url VARCHAR(500),
            estado VARCHAR(20) DEFAULT 'procesando',
            mensaje_error VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Pagos
        "ALTER TABLE pagos ADD COLUMN IF NOT EXISTS metodo_pago VARCHAR(30)",
        # QR Pago Config
        """
        CREATE TABLE IF NOT EXISTS qr_pago_config (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER,
            imagen_url VARCHAR(500) NOT NULL,
            banco_destino VARCHAR(100),
            titular VARCHAR(150),
            activo BOOLEAN DEFAULT TRUE,
            sucursal_id INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "ALTER TABLE qr_pago_config ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
    ]
    for stmt in statements:
        try:
            db.execute(text(stmt))
            db.commit()
        except Exception:
            db.rollback()
            # SQLite fallback: en sqlite 'ADD COLUMN IF NOT EXISTS' puede no ser soportado
            # así que intentamos sin 'IF NOT EXISTS'
            sqlite_stmt = stmt.replace(" IF NOT EXISTS", "")
            try:
                db.execute(text(sqlite_stmt))
                db.commit()
            except Exception:
                db.rollback()


def init_db():
    """Create all tables and seed default permissions and admin user."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Run defensive column migrations
        _run_column_migrations(db)

        # Seed the legacy tenant before assigning existing records.
        from app.models.empresa import Empresa
        default_empresa = db.query(Empresa).filter(Empresa.codigo == "stylestore").first()
        if not default_empresa:
            default_empresa = Empresa(codigo="stylestore", nombre="StyleStore", active=True)
            db.add(default_empresa)
            db.commit()
            db.refresh(default_empresa)

        from app.models.sucursal import Sucursal
        db.query(User).filter(User.empresa_id.is_(None)).update(
            {User.empresa_id: default_empresa.id}, synchronize_session=False
        )
        db.query(Sucursal).filter(Sucursal.empresa_id.is_(None)).update(
            {Sucursal.empresa_id: default_empresa.id}, synchronize_session=False
        )
        from app.models.categoria import Categoria
        from app.models.color import Color
        from app.models.talla import Talla
        from app.models.temporada import Temporada
        from app.models.coleccion import Coleccion
        from app.models.producto import Producto
        from app.models.proveedor import Proveedor
        from app.models.qr_pago_config import QRPagoConfig
        from app.models.bitacora import Bitacora
        from app.models.pago import Pago
        for model in (Categoria, Color, Talla, Temporada, Coleccion, Producto, Proveedor, QRPagoConfig, Bitacora):
            db.query(model).filter(model.empresa_id.is_(None)).update(
                {model.empresa_id: default_empresa.id}, synchronize_session=False
            )
        db.commit()
        db.execute(text("""
            UPDATE pagos SET empresa_id = sucursales.empresa_id
            FROM orden_venta, sucursales
            WHERE pagos.orden_venta_id = orden_venta.id
              AND orden_venta.sucursal_id = sucursales.id
              AND pagos.empresa_id IS NULL
        """))
        db.query(Pago).filter(Pago.empresa_id.is_(None)).update(
            {Pago.empresa_id: default_empresa.id}, synchronize_session=False
        )
        for pago in db.query(Pago).filter(Pago.estado == "aprobado", Pago.recibo_numero.is_(None)).all():
            pago.recibo_numero = f"REC-{pago.id:08d}"
        db.commit()

        # Seed permissions and roles
        role_service = RoleService(db)
        role_service.seed_default_permissions_and_roles()

        from app.services.plan_service import PlanService
        PlanService(db).seed_global_plans()

        # Seed default backup configuration if not exists
        from app.models.backup_config import BackupConfig
        cfg = db.query(BackupConfig).first()
        if not cfg:
            cfg = BackupConfig(
                auto_backup_enabled=False,
                frequency_hours=24,
                retention_days=30,
            )
            db.add(cfg)
            db.commit()

        # Seed default QR de cobro en mostrador if not exists
        qr_cfg = db.query(QRPagoConfig).first()
        if not qr_cfg:
            qr_cfg = QRPagoConfig(
                imagen_url="/uploads/qr/qr_mostrador_default.png",
                banco_destino="Red Enlace / Banco Unión / BNB / BCP",
                titular="StyleStore Bolivia",
                activo=True,
                sucursal_id=1,
                empresa_id=default_empresa.id,
            )
            db.add(qr_cfg)
            db.commit()
            logger.info("Created default QR Pago Config: /uploads/qr/qr_mostrador_default.png")

        # Seed initial admin if none exists
        admin_user = db.query(User).filter(User.role == "administrador").first()
        if not admin_user:
            if settings.INITIAL_ADMIN_EMAIL and settings.INITIAL_ADMIN_PASSWORD:
                admin_user = User(
                    email=settings.INITIAL_ADMIN_EMAIL,
                    name="Administrador StyleStore",
                    hashed_password=hash_password(settings.INITIAL_ADMIN_PASSWORD),
                    role="administrador",
                    empresa_id=default_empresa.id,
                    is_platform_admin=True,
                    is_active=True,
                )
                db.add(admin_user)
                db.commit()
                logger.info("Created initial administrator from environment configuration")
            else:
                logger.warning(
                    "No administrator exists and bootstrap credentials are not configured; "
                    "set INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD explicitly"
                )
        elif not db.query(User).filter(User.is_platform_admin == True).first():
            admin_user.is_platform_admin = True
            if admin_user.empresa_id is None:
                admin_user.empresa_id = default_empresa.id
            db.commit()
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
