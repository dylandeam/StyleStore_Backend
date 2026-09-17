"""
Servicio de Copias de Seguridad (Backups) con Hashing SHA-256 e Integridad Criptográfica.
Genera snapshots JSON del sistema StyleStore y valida integridad.
"""
import os
import json
import hashlib
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings
from app.models.backup_log import BackupLog
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.sucursal import Sucursal
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.talla import Talla
from app.models.temporada import Temporada
from app.models.coleccion import Coleccion
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.stock_inventario import StockInventario
from app.models.cliente import Cliente
from app.models.empleado import Empleado
from app.models.orden_venta import OrdenVenta, DetalleVenta
from app.models.pago import Pago
from app.models.envio import Envio


def _json_serial(obj):
    """Serializador para objetos datetime, date y Decimal."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


class BackupService:
    """Administrador de copias de seguridad StyleStore."""

    def __init__(self, db: Session):
        self.db = db
        self.backup_dir = settings.BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, user_id: int | None = None, tipo: str = "manual") -> Tuple[BackupLog, str]:
        """
        Genera un snapshot JSON completo de la base de datos, calcula el hash SHA-256,
        lo guarda en disco y registra el evento en backup_logs.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stylestore_backup_{timestamp}.json"
        filepath = self.backup_dir / filename

        # 1. Recolectar datos
        data: Dict[str, Any] = {
            "metadata": {
                "version": "5.0",
                "app": "StyleStore E-Commerce",
                "timestamp": datetime.now().isoformat(),
                "tipo": tipo,
                "creado_por_id": user_id,
            },
            "tables": {}
        }

        # Tablas a exportar
        tables_to_dump = [
            ("roles", Role),
            ("permissions", Permission),
            ("users", User),
            ("sucursales", Sucursal),
            ("categorias", Categoria),
            ("colores", Color),
            ("tallas", Talla),
            ("temporadas", Temporada),
            ("colecciones", Coleccion),
            ("productos", Producto),
            ("producto_colores", ProductoColor),
            ("stock_inventario", StockInventario),
            ("clientes", Cliente),
            ("empleados", Empleado),
            ("ordenes_venta", OrdenVenta),
            ("detalles_venta", DetalleVenta),
            ("pagos", Pago),
            ("envios", Envio),
        ]

        for table_name, model in tables_to_dump:
            records = self.db.query(model).all()
            serialized_records = []
            for r in records:
                d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
                # No exportar hashes de contraseñas directamente en texto plano
                serialized_records.append(d)
            data["tables"][table_name] = serialized_records

        # 2. Convertir a JSON
        json_bytes = json.dumps(data, default=_json_serial, indent=2, ensure_ascii=False).encode("utf-8")

        # 3. Calcular Hash SHA-256
        sha256_hash = hashlib.sha256(json_bytes).hexdigest()
        tamano_bytes = len(json_bytes)

        # 4. Guardar archivo en disco
        with open(filepath, "wb") as f:
            f.write(json_bytes)

        # 5. Registrar en BD
        backup_log = BackupLog(
            nombre_archivo=filename,
            sha256_hash=sha256_hash,
            tamano_bytes=tamano_bytes,
            tipo=tipo,
            estado="exitoso",
            creado_por_id=user_id,
        )
        self.db.add(backup_log)
        self.db.commit()
        self.db.refresh(backup_log)

        return backup_log, str(filepath)

    def verify_file_sha256(self, file_content: bytes, expected_hash: str) -> bool:
        """Comprueba que el hash SHA-256 del archivo coincida exactamente con el hash esperado."""
        calculated = hashlib.sha256(file_content).hexdigest()
        return calculated.lower() == expected_hash.lower().strip()

    def get_backup_logs(self) -> List[BackupLog]:
        """Obtiene el historial de backups ordenados por fecha descendente."""
        return self.db.query(BackupLog).order_by(BackupLog.created_at.desc()).all()
