"""
Backups endpoints.
Generación, descarga y verificación de integridad criptográfica SHA-256 de respaldos de base de datos.
"""
from pathlib import Path
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.backup_log import BackupLog
from app.services.backup_service import BackupService
from app.services.bitacora_service import BitacoraService
from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundException, BadRequestException

router = APIRouter(prefix="/backups", tags=["Backups"])


class BackupVerifyRequest(BaseModel):
    id: int
    expected_hash: str


@router.post("/generar", summary="Generar copia de seguridad con hash SHA-256")
async def generate_backup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Genera un snapshot JSON completo de la base de datos, calcula su hash SHA-256
    y lo almacena para descarga segura.
    """
    service = BackupService(db)
    backup_log, filepath = service.create_backup(user_id=current_user.id, tipo="manual")

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Generó respaldo de seguridad '{backup_log.nombre_archivo}' con SHA-256: {backup_log.sha256_hash[:12]}...",
        module="seguridad",
    )

    return {
        "id": backup_log.id,
        "nombre_archivo": backup_log.nombre_archivo,
        "sha256_hash": backup_log.sha256_hash,
        "tamano_bytes": backup_log.tamano_bytes,
        "tipo": backup_log.tipo,
        "created_at": backup_log.created_at,
        "mensaje": "Copia de seguridad creada exitosamente con verificación de integridad.",
    }


@router.get("", summary="Listar copias de seguridad registradas")
async def list_backups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna el historial de copias de seguridad generadas."""
    service = BackupService(db)
    logs = service.get_backup_logs()
    return [
        {
            "id": log.id,
            "nombre_archivo": log.nombre_archivo,
            "sha256_hash": log.sha256_hash,
            "tamano_bytes": log.tamano_bytes,
            "tipo": log.tipo,
            "estado": log.estado,
            "creado_por": log.usuario.name if log.usuario else "Sistema",
            "created_at": log.created_at,
        }
        for log in logs
    ]


@router.get("/{backup_id}/descargar", summary="Descargar archivo de copia de seguridad")
async def download_backup(
    backup_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permite descargar el archivo JSON de respaldo verificado."""
    log = db.query(BackupLog).filter(BackupLog.id == backup_id).first()
    if not log:
        raise NotFoundException(f"Registro de respaldo con ID {backup_id} no encontrado.")

    service = BackupService(db)
    filepath = service.backup_dir / log.nombre_archivo

    if not filepath.exists():
        raise NotFoundException(f"El archivo físico {log.nombre_archivo} no se encuentra en el servidor.")

    return FileResponse(
        path=filepath,
        filename=log.nombre_archivo,
        media_type="application/json",
        headers={"X-SHA256-Checksum": log.sha256_hash},
    )


@router.post("/verificar", summary="Verificar integridad de copia de seguridad con SHA-256")
async def verify_backup_integrity(
    payload: BackupVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Comprueba que el hash SHA-256 del archivo coincida con el hash proporcionado o registrado."""
    log = db.query(BackupLog).filter(BackupLog.id == payload.id).first()
    if not log:
        raise NotFoundException(f"Respaldo con ID {payload.id} no encontrado.")

    service = BackupService(db)
    filepath = service.backup_dir / log.nombre_archivo
    if not filepath.exists():
        raise NotFoundException("Archivo físico no encontrado.")

    with open(filepath, "rb") as f:
        file_bytes = f.read()

    is_valid = service.verify_file_sha256(file_bytes, payload.expected_hash)

    return {
        "id": log.id,
        "nombre_archivo": log.nombre_archivo,
        "registrado_sha256": log.sha256_hash,
        "comprobado_sha256": payload.expected_hash,
        "es_valido": is_valid,
        "mensaje": "Integridad criptográfica comprobada con éxito." if is_valid else "¡Alerta! El hash no coincide con el archivo.",
    }
