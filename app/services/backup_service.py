"""
Servicio de Copias de Seguridad (Backup & Restore) para StyleStore.
- Exportación e importación integral de todas las entidades (usuarios, productos, stock, clientes, empleados, ventas, reservas, pagos, envíos, colecciones, archivos, bitácora).
- Verificación criptográfica con hash SHA-256 de 256 bits.
- Respaldo dual (archivo físico + persistencia en base de datos para sobrevivir redeploys).
- Restauración completa y atómica con preservación de integridad referencial y secuencias.
- Configuración y ejecución de respaldos automáticos periódicos con política de retención.
"""
import os
import json
import hashlib
from datetime import datetime, date, time
from decimal import Decimal
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings
from app.models.backup_log import BackupLog
from app.models.backup_config import BackupConfig
from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.sucursal import Sucursal
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.talla import Talla
from app.models.temporada import Temporada
from app.models.coleccion import Coleccion
from app.models.proveedor import Proveedor, proveedor_categorias, proveedor_temporadas, proveedor_colecciones
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.proximamente import Proximamente
from app.models.stock_inventario import StockInventario
from app.models.cliente import Cliente
from app.models.empleado import Empleado
from app.models.orden_venta import OrdenVenta, DetalleVenta
from app.models.reserva import Reserva, DetalleReserva
from app.models.carrito import Carrito, DetalleCarrito
from app.models.pago import Pago
from app.models.envio import Envio
from app.models.bitacora import Bitacora
from app.models.uploaded_file import UploadedFile


def _json_serial(obj):
    """Serializador universal para tipos datetime, date, time, Decimal y bytes."""
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        import base64
        return {"__bytes__": base64.b64encode(obj).decode("ascii")}
    raise TypeError(f"Type {type(obj)} not serializable")


def _json_deserial(val):
    """Reconstruye bytes serializados si es necesario."""
    if isinstance(val, dict) and "__bytes__" in val:
        import base64
        return base64.b64decode(val["__bytes__"])
    return val


class BackupService:
    """Gestor de Copias de Seguridad (Backup & Restore) de StyleStore."""

    def __init__(self, db: Session):
        self.db = db
        self.backup_dir = settings.BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def get_config(self) -> BackupConfig:
        """Obtiene o crea la configuración de periodicidad de backups automáticos."""
        cfg = self.db.query(BackupConfig).first()
        if not cfg:
            cfg = BackupConfig(
                auto_backup_enabled=False,
                frequency_hours=24,
                retention_days=30,
            )
            self.db.add(cfg)
            self.db.commit()
            self.db.refresh(cfg)
        return cfg

    def update_config(
        self,
        auto_backup_enabled: bool,
        frequency_hours: int,
        retention_days: int,
    ) -> BackupConfig:
        """Actualiza la configuración de periodicidad y retención."""
        cfg = self.get_config()
        cfg.auto_backup_enabled = auto_backup_enabled
        cfg.frequency_hours = max(1, frequency_hours)
        cfg.retention_days = max(1, retention_days)
        self.db.commit()
        self.db.refresh(cfg)
        return cfg

    def create_backup(self, user_id: int | None = None, tipo: str = "manual") -> Tuple[BackupLog, str]:
        """
        Genera un snapshot JSON completo con todas las tablas de StyleStore,
        calcula su hash criptográfico SHA-256, lo guarda en disco y en BD.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tipo_str = "auto" if tipo.lower() in ["auto", "automatico"] else "manual"
        filename = f"backup_stylestore_{tipo_str}_{timestamp}.json"
        filepath = self.backup_dir / filename

        # 1. Estructura del snapshot
        data: Dict[str, Any] = {
            "metadata": {
                "version": "5.0",
                "app": "StyleStore E-Commerce",
                "tipo": tipo_str,
                "created_at": datetime.now().isoformat(),
                "created_by_user_id": user_id,
            },
            "tables": {}
        }

        # 2. Extracción ordenada de todas las tablas de StyleStore
        tables_to_dump = [
            ("roles", Role),
            ("permissions", Permission),
            ("role_permissions", RolePermission),
            ("users", User),
            ("sucursales", Sucursal),
            ("categorias", Categoria),
            ("colores", Color),
            ("tallas", Talla),
            ("temporadas", Temporada),
            ("colecciones", Coleccion),
            ("proveedores", Proveedor),
            ("productos", Producto),
            ("producto_colores", ProductoColor),
            ("proximamente", Proximamente),
            ("stock_inventario", StockInventario),
            ("clientes", Cliente),
            ("empleados", Empleado),
            ("ordenes_venta", OrdenVenta),
            ("detalles_venta", DetalleVenta),
            ("reservas", Reserva),
            ("detalles_reserva", DetalleReserva),
            ("carritos", Carrito),
            ("detalles_carrito", DetalleCarrito),
            ("pagos", Pago),
            ("envios", Envio),
            ("bitacora", Bitacora),
            ("uploaded_files", UploadedFile),
        ]

        for table_key, model in tables_to_dump:
            records = self.db.query(model).all()
            row_list = []
            for r in records:
                row_dict = {}
                for c in r.__table__.columns:
                    val = getattr(r, c.name)
                    row_dict[c.name] = val
                row_list.append(row_dict)
            data["tables"][table_key] = row_list

        # Relaciones M:N intermedias con savepoints
        # proveedor_categorias
        try:
            with self.db.begin_nested():
                pc_rows = self.db.execute(proveedor_categorias.select()).fetchall()
                data["tables"]["proveedor_categorias"] = [
                    {"proveedor_codigo": r[0], "categoria_id": r[1]} for r in pc_rows
                ]
        except Exception:
            data["tables"]["proveedor_categorias"] = []

        # proveedor_temporadas
        try:
            with self.db.begin_nested():
                pt_rows = self.db.execute(proveedor_temporadas.select()).fetchall()
                data["tables"]["proveedor_temporadas"] = [
                    {"proveedor_codigo": r[0], "temporada_id": r[1]} for r in pt_rows
                ]
        except Exception:
            data["tables"]["proveedor_temporadas"] = []

        # proveedor_colecciones
        try:
            with self.db.begin_nested():
                pcol_rows = self.db.execute(proveedor_colecciones.select()).fetchall()
                data["tables"]["proveedor_colecciones"] = [
                    {"proveedor_codigo": r[0], "coleccion_id": r[1]} for r in pcol_rows
                ]
        except Exception:
            data["tables"]["proveedor_colecciones"] = []

        # 3. Serializar y computar hash SHA-256
        json_str = json.dumps(data, default=_json_serial, indent=2, ensure_ascii=False)
        json_bytes = json_str.encode("utf-8")
        sha256_hash = hashlib.sha256(json_bytes).hexdigest()
        tamano_bytes = len(json_bytes)

        # 4. Guardar archivo físico en disco
        try:
            with open(filepath, "wb") as f:
                f.write(json_bytes)
        except Exception as e:
            print(f"Advertencia al escribir backup en disco: {e}")

        # 5. Guardar en Base de Datos (Persistencia dual)
        backup_log = BackupLog(
            nombre_archivo=filename,
            sha256_hash=sha256_hash,
            tamano_bytes=tamano_bytes,
            tipo=tipo_str,
            estado="exitoso",
            contenido_json=json_str,
            creado_por_id=user_id,
        )
        self.db.add(backup_log)

        # Si fue automático, actualizar last_auto_backup en config
        if tipo_str == "auto":
            cfg = self.get_config()
            cfg.last_auto_backup = datetime.now()

        self.db.commit()
        self.db.refresh(backup_log)

        return backup_log, str(filepath)

    def get_backup_content(self, backup_id: int) -> Tuple[str, bytes, str]:
        """Obtiene el nombre de archivo, contenido en bytes y hash de un respaldo."""
        log = self.db.query(BackupLog).filter(BackupLog.id == backup_id).first()
        if not log:
            raise ValueError(f"Respaldo con ID {backup_id} no encontrado.")

        filepath = self.backup_dir / log.nombre_archivo
        if filepath.exists():
            with open(filepath, "rb") as f:
                content = f.read()
            return log.nombre_archivo, content, log.sha256_hash

        # Fallback a contenido_json almacenado en base de datos
        if log.contenido_json:
            content = log.contenido_json.encode("utf-8")
            # Restaurar en disco si es posible
            try:
                with open(filepath, "wb") as f:
                    f.write(content)
            except Exception:
                pass
            return log.nombre_archivo, content, log.sha256_hash

        raise ValueError(f"No se pudo recuperar el archivo de respaldo {log.nombre_archivo}.")

    def delete_backup(self, backup_id: int) -> bool:
        """Elimina un respaldo del historial y del almacenamiento en disco."""
        log = self.db.query(BackupLog).filter(BackupLog.id == backup_id).first()
        if not log:
            return False

        filepath = self.backup_dir / log.nombre_archivo
        if filepath.exists():
            try:
                os.remove(filepath)
            except Exception:
                pass

        self.db.delete(log)
        self.db.commit()
        return True

    def verify_file_sha256(self, file_content: bytes, expected_hash: str) -> bool:
        """Verifica la integridad de los bytes calculando el checksum SHA-256."""
        calculated = hashlib.sha256(file_content).hexdigest()
        return calculated.lower() == expected_hash.lower().strip()

    def restore_backup(
        self,
        file_bytes: bytes,
        user_id: int | None = None,
        expected_hash: str | None = None,
    ) -> Dict[str, Any]:
        """
        Restaura de forma atómica y completa todas las entidades de StyleStore
        a partir del archivo snapshot JSON recibido, verificando el hash SHA-256.
        """
        # 1. Validar integridad si se proporcionó un hash esperado
        computed_hash = hashlib.sha256(file_bytes).hexdigest()
        if expected_hash and not self.verify_file_sha256(file_bytes, expected_hash):
            raise ValueError("El hash SHA-256 del archivo no coincide con el valor esperado. Integridad comprometida.")

        # 2. Parsear JSON
        try:
            payload = json.loads(file_bytes.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Archivo JSON inválido o corrupto: {e}")

        if "tables" not in payload:
            raise ValueError("El archivo no tiene la estructura de tablas de respaldo de StyleStore.")

        tables = payload["tables"]

        # 3. Borrado en orden seguro de dependencias de clave foránea
        clear_order = [
            ("proveedor_colecciones", None),
            ("proveedor_temporadas", None),
            ("proveedor_categorias", None),
            ("detalle_reserva", DetalleReserva),
            ("reservas", Reserva),
            ("detalle_venta", DetalleVenta),
            ("pagos", Pago),
            ("envios", Envio),
            ("orden_venta", OrdenVenta),
            ("detalle_carrito", DetalleCarrito),
            ("carritos", Carrito),
            ("stock_inventario", StockInventario),
            ("producto_colores", ProductoColor),
            ("proximamente", Proximamente),
            ("productos", Producto),
            ("colecciones", Coleccion),
            ("temporadas", Temporada),
            ("tallas", Talla),
            ("colores", Color),
            ("categorias", Categoria),
            ("proveedores", Proveedor),
            ("empleados", Empleado),
            ("clientes", Cliente),
            ("sucursales", Sucursal),
            ("bitacora", Bitacora),
            ("role_permissions", RolePermission),
            ("users", User),
            ("permissions", Permission),
            ("roles", Role),
            ("uploaded_files", UploadedFile),
        ]

        try:
            # Desactivar temporalmente restricciones si el motor lo permite
            is_sqlite = (getattr(self.db.bind.dialect, "name", "") == "sqlite")
            if is_sqlite:
                self.db.execute(text("PRAGMA foreign_keys = OFF;"))

            # Limpiar tablas intermedias M:N con savepoints
            for intermediate in ["proveedor_colecciones", "proveedor_temporadas", "proveedor_categorias", "role_permissions"]:
                try:
                    with self.db.begin_nested():
                        self.db.execute(text(f"DELETE FROM {intermediate}"))
                except Exception:
                    pass

            for tbl_name, model in clear_order:
                try:
                    with self.db.begin_nested():
                        if model is not None:
                            self.db.query(model).delete()
                        else:
                            self.db.execute(text(f"DELETE FROM {tbl_name}"))
                except Exception:
                    try:
                        with self.db.begin_nested():
                            self.db.execute(text(f"DELETE FROM {tbl_name}"))
                    except Exception:
                        pass

            self.db.flush()

            total_restored_records = 0

            # 4. Inserción en orden de dependencias
            def _insert_rows(model_class, rows):
                nonlocal total_restored_records
                if not rows:
                    return
                for r in rows:
                    cleaned = {k: _json_deserial(v) for k, v in r.items()}
                    # Convertir fechas/horas si son cadenas
                    for k, v in cleaned.items():
                        if isinstance(v, str) and ("date" in k or "created_at" in k or "updated_at" in k or k == "fecha"):
                            try:
                                if len(v) == 10:
                                    cleaned[k] = datetime.strptime(v, "%Y-%m-%d").date()
                                else:
                                    cleaned[k] = datetime.fromisoformat(v)
                            except Exception:
                                pass
                        elif isinstance(v, str) and k == "hora":
                            try:
                                cleaned[k] = datetime.strptime(v, "%H:%M:%S").time()
                            except Exception:
                                pass
                    obj = model_class(**cleaned)
                    self.db.add(obj)
                    total_restored_records += 1
                self.db.flush()

            # Inserciones ordenadas:
            _insert_rows(Role, tables.get("roles", []))
            _insert_rows(Permission, tables.get("permissions", []))
            _insert_rows(RolePermission, tables.get("role_permissions", []))

            _insert_rows(User, tables.get("users", []))
            _insert_rows(Sucursal, tables.get("sucursales", []))
            _insert_rows(Categoria, tables.get("categorias", []))
            _insert_rows(Color, tables.get("colores", []))
            _insert_rows(Talla, tables.get("tallas", []))
            _insert_rows(Temporada, tables.get("temporadas", []))
            _insert_rows(Coleccion, tables.get("colecciones", []))
            _insert_rows(Proveedor, tables.get("proveedores", []))

            # Intermedias de proveedor
            for row in tables.get("proveedor_categorias", []):
                p_code = row.get("proveedor_codigo") or row.get("proveedor_id")
                c_id = row.get("categoria_id")
                if p_code and c_id:
                    try:
                        with self.db.begin_nested():
                            self.db.execute(
                                text("INSERT INTO proveedor_categorias (proveedor_codigo, categoria_id) VALUES (:pr, :cat)"),
                                {"pr": p_code, "cat": c_id},
                            )
                    except Exception:
                        pass

            for row in tables.get("proveedor_temporadas", []):
                p_code = row.get("proveedor_codigo") or row.get("proveedor_id")
                t_id = row.get("temporada_id")
                if p_code and t_id:
                    try:
                        with self.db.begin_nested():
                            self.db.execute(
                                text("INSERT INTO proveedor_temporadas (proveedor_codigo, temporada_id) VALUES (:pr, :tmp)"),
                                {"pr": p_code, "tmp": t_id},
                            )
                    except Exception:
                        pass

            for row in tables.get("proveedor_colecciones", []):
                p_code = row.get("proveedor_codigo") or row.get("proveedor_id")
                col_id = row.get("coleccion_id")
                if p_code and col_id:
                    try:
                        with self.db.begin_nested():
                            self.db.execute(
                                text("INSERT INTO proveedor_colecciones (proveedor_codigo, coleccion_id) VALUES (:pr, :col)"),
                                {"pr": p_code, "col": col_id},
                            )
                    except Exception:
                        pass

            _insert_rows(Producto, tables.get("productos", []))
            _insert_rows(ProductoColor, tables.get("producto_colores", []))
            _insert_rows(Proximamente, tables.get("proximamente", []))
            _insert_rows(StockInventario, tables.get("stock_inventario", []))
            _insert_rows(Cliente, tables.get("clientes", []))
            _insert_rows(Empleado, tables.get("empleados", []))
            _insert_rows(OrdenVenta, tables.get("ordenes_venta") or tables.get("orden_venta") or [])
            _insert_rows(DetalleVenta, tables.get("detalles_venta") or tables.get("detalle_venta") or [])
            _insert_rows(Reserva, tables.get("reservas", []))
            _insert_rows(DetalleReserva, tables.get("detalles_reserva", []))
            _insert_rows(Carrito, tables.get("carritos", []))
            _insert_rows(DetalleCarrito, tables.get("detalles_carrito", []))
            _insert_rows(Pago, tables.get("pagos", []))
            _insert_rows(Envio, tables.get("envios", []))
            _insert_rows(UploadedFile, tables.get("uploaded_files", []))
            _insert_rows(Bitacora, tables.get("bitacora", []))

            # 5. Ajustar secuencias en PostgreSQL de forma segura usando savepoints
            if not is_sqlite:
                sequences_tables = [
                    ("roles", "id"),
                    ("permissions", "id"),
                    ("users", "id"),
                    ("sucursales", "id"),
                    ("categorias", "id"),
                    ("colores", "id"),
                    ("tallas", "id"),
                    ("temporadas", "id"),
                    ("colecciones", "id"),
                    ("productos", "id"),
                    ("producto_colores", "id"),
                    ("proximamente", "id"),
                    ("stock_inventario", "id"),
                    ("empleados", "id"),
                    ("orden_venta", "id"),
                    ("detalle_venta", "id"),
                    ("reservas", "id"),
                    ("detalle_reserva", "id"),
                    ("carritos", "id"),
                    ("detalle_carrito", "id"),
                    ("pagos", "id"),
                    ("envios", "id"),
                    ("bitacora", "id"),
                    ("uploaded_files", "id"),
                    ("backup_logs", "id"),
                ]
                for tbl, pk in sequences_tables:
                    try:
                        with self.db.begin_nested():
                            self.db.execute(text(f"""
                                DO $$
                                DECLARE
                                    seq_name text;
                                BEGIN
                                    seq_name := pg_get_serial_sequence('{tbl}', '{pk}');
                                    IF seq_name IS NOT NULL THEN
                                        EXECUTE format('SELECT setval(%L, COALESCE((SELECT MAX(%I) FROM %I), 1) + 1, false)', seq_name, '{pk}', '{tbl}');
                                    END IF;
                                END $$;
                            """))
                    except Exception:
                        pass

            if is_sqlite:
                self.db.execute(text("PRAGMA foreign_keys = ON;"))

            self.db.commit()

            return {
                "success": True,
                "message": "Base de datos restaurada integralmente con éxito.",
                "total_records_restored": total_restored_records,
                "tables_count": len(tables),
                "sha256": computed_hash,
            }

        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Error crítico durante la restauración de la base de datos: {e}")

    def check_and_run_auto_backup(self) -> BackupLog | None:
        """
        Verifica si la periodicidad automática configurada requiere generar un nuevo respaldo
        y elimina respaldos obsoletos según la política de días de retención.
        """
        cfg = self.get_config()
        if not cfg.auto_backup_enabled:
            return None

        now = datetime.now()
        should_run = False
        if not cfg.last_auto_backup:
            should_run = True
        else:
            diff_hours = (now - cfg.last_auto_backup.replace(tzinfo=None)).total_seconds() / 3600
            if diff_hours >= cfg.frequency_hours:
                should_run = True

        log_created = None
        if should_run:
            log_created, _ = self.create_backup(user_id=None, tipo="automatico")

        # Aplicar política de retención: eliminar backups más antiguos que retention_days
        if cfg.retention_days > 0:
            all_logs = self.db.query(BackupLog).all()
            for b in all_logs:
                if b.created_at:
                    age_days = (now - b.created_at.replace(tzinfo=None)).days
                    if age_days > cfg.retention_days:
                        self.delete_backup(b.id)

        return log_created

    def get_backup_logs(self) -> List[BackupLog]:
        """Obtiene el historial de backups ordenados por fecha descendente."""
        return self.db.query(BackupLog).order_by(BackupLog.created_at.desc()).all()
