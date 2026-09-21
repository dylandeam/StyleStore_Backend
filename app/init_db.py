"""
Database initialization and default admin / permissions seeder.
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal, Base, engine
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
        # Bitacora
        "ALTER TABLE bitacora ADD COLUMN IF NOT EXISTS ip_address VARCHAR(50)",
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
        # Pagos
        "ALTER TABLE pagos ADD COLUMN IF NOT EXISTS paypal_capture_id VARCHAR(100)",
        "ALTER TABLE pagos ADD COLUMN IF NOT EXISTS metodo_pago VARCHAR(50)",
        # Clientes
        "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS foto VARCHAR(255)",
        # Sucursales
        "ALTER TABLE sucursales ADD COLUMN IF NOT EXISTS latitud NUMERIC(10, 6)",
        "ALTER TABLE sucursales ADD COLUMN IF NOT EXISTS longitud NUMERIC(10, 6)",
        "ALTER TABLE sucursales ADD COLUMN IF NOT EXISTS maps_url VARCHAR(500)",
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
        # Productos (Vestidor Virtual y Fotos Frontal/Trasera)
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS foto_trasera VARCHAR(255)",
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS foto_vestidor_frontal VARCHAR(255)",
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS foto_vestidor_trasera VARCHAR(255)",
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS tipo_prenda VARCHAR(30) DEFAULT 'superior'",
        # Pagos
        "ALTER TABLE pagos ADD COLUMN IF NOT EXISTS metodo_pago VARCHAR(30)",
        # QR Pago Config
        """
        CREATE TABLE IF NOT EXISTS qr_pago_config (
            id SERIAL PRIMARY KEY,
            imagen_url VARCHAR(500) NOT NULL,
            banco_destino VARCHAR(100),
            titular VARCHAR(150),
            activo BOOLEAN DEFAULT TRUE,
            sucursal_id INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """,
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

        # Seed permissions and roles
        role_service = RoleService(db)
        role_service.seed_default_permissions_and_roles()

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

        # Seed initial admin if none exists
        admin_user = db.query(User).filter(User.role == "administrador").first()
        if not admin_user:
            admin_user = User(
                email="admin@stylestore.com",
                name="Administrador StyleStore",
                hashed_password=hash_password("Admin@1234"),
                role="administrador",
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            logger.info("Created default administrator user: admin@stylestore.com / Admin@1234")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
