"""
Backups endpoints.
Generación, descarga, restauración y configuración de periodicidad automática con verificación SHA-256.
"""
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.backup_log import BackupLog
from app.services.backup_service import BackupService
from app.services.bitacora_service import BitacoraService
from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundException, BadRequestException, ForbiddenException

router = APIRouter(prefix="/backups", tags=["Backups"])


class BackupConfigRequest(BaseModel):
    auto_backup_enabled: bool
    frequency_hours: int = Field(24, ge=1, le=720)
    retention_days: int = Field(30, ge=1, le=365)


class BackupVerifyRequest(BaseModel):
    id: int
    expected_hash: str


@router.post("/generar", summary="Generar copia de seguridad inmediata con hash SHA-256")
async def generate_backup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Genera un snapshot JSON completo e integral de StyleStore (clientes, productos, ventas, etc.),
    calcula su hash SHA-256 y lo almacena con persistencia dual.
    """
    if current_user.role != "administrador":
        raise ForbiddenException("Solo el administrador puede generar respaldos del sistema.")

    service = BackupService(db)
    backup_log, filepath = service.create_backup(user_id=current_user.id, tipo="manual")

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Generó respaldo de seguridad manual '{backup_log.nombre_archivo}' con hash SHA-256",
        module="seguridad",
    )

    return {
        "id": backup_log.id,
        "nombre_archivo": backup_log.nombre_archivo,
        "sha256_hash": backup_log.sha256_hash,
        "tamano_bytes": backup_log.tamano_bytes,
        "tipo": backup_log.tipo,
        "estado": backup_log.estado,
        "created_at": backup_log.created_at,
        "mensaje": "Copia de seguridad integral creada exitosamente con verificación de integridad.",
    }


@router.get("", summary="Listar copias de seguridad registradas")
async def list_backups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna el historial de copias de seguridad generadas y ejecuta comprobación automática si aplica."""
    if current_user.role != "administrador":
        raise ForbiddenException("Solo el administrador puede ver el historial de respaldos.")

    service = BackupService(db)
    # Ejecutar verificación de respaldo automático si está configurado
    try:
        service.check_and_run_auto_backup()
    except Exception as e:
        print(f"Aviso en check_and_run_auto_backup: {e}")

    logs = service.get_backup_logs()
    return [
        {
            "id": log.id,
            "nombre_archivo": log.nombre_archivo,
            "sha256_hash": log.sha256_hash,
            "tamano_bytes": log.tamano_bytes,
            "tipo": log.tipo,
            "estado": log.estado,
            "creado_por": log.usuario.name if log.usuario else ("Automático (Sistema)" if log.tipo == "auto" else "Sistema"),
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
    """Descarga el archivo JSON de respaldo verificado."""
    if current_user.role != "administrador":
        raise ForbiddenException("Solo el administrador puede descargar respaldos del sistema.")

    service = BackupService(db)
    try:
        filename, content_bytes, sha256_hash = service.get_backup_content(backup_id)
    except ValueError as e:
        raise NotFoundException(str(e))

    return Response(
        content=content_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-SHA256-Checksum": sha256_hash,
        },
    )


@router.post("/{backup_id}/restaurar", summary="Restaurar copia de seguridad desde el historial del servidor")
async def restore_from_server(
    backup_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Restaura la base de datos completa a partir de un respaldo existente en el servidor."""
    if current_user.role != "administrador":
        raise ForbiddenException("Solo el administrador puede restaurar la base de datos.")

    user_snapshot = f"{current_user.name} ({current_user.email})"
    user_id = current_user.id

    service = BackupService(db)
    try:
        filename, content_bytes, sha256_hash = service.get_backup_content(backup_id)
    except ValueError as e:
        raise NotFoundException(str(e))

    try:
        result = service.restore_backup(content_bytes, user_id=user_id, expected_hash=sha256_hash)
    except Exception as e:
        raise BadRequestException(f"Fallo al restaurar respaldo: {e}")

    try:
        BitacoraService.registrar(
            db=db,
            user=user_snapshot,
            action=f"Restauró la base de datos completa desde el respaldo en servidor '{filename}'",
            module="seguridad",
        )
    except Exception:
        db.rollback()

    return result


@router.post("/subir-restaurar", summary="Cargar archivo JSON y restaurar base de datos")
async def upload_and_restore(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Recibe un archivo .json subido por el usuario, valida su hash SHA-256 e integridad,
    y restaura todas las tablas de StyleStore.
    """
    if current_user.role != "administrador":
        raise ForbiddenException("Solo el administrador puede restaurar copias de seguridad.")

    if not file.filename.endswith(".json"):
        raise BadRequestException("Solo se permiten archivos de respaldo en formato .json.")

    content = await file.read()
    if not content:
        raise BadRequestException("El archivo cargado está vacío.")

    user_snapshot = f"{current_user.name} ({current_user.email})"
    user_id = current_user.id

    service = BackupService(db)
    try:
        result = service.restore_backup(content, user_id=user_id)
    except Exception as e:
        raise BadRequestException(f"Error al procesar y restaurar el respaldo: {e}")

    try:
        BitacoraService.registrar(
            db=db,
            user=user_snapshot,
            action=f"Restauró la base de datos subiendo el archivo externo '{file.filename}'",
            module="seguridad",
        )
    except Exception:
        pass

    return result


@router.delete("/{backup_id}", summary="Eliminar copia de seguridad")
async def delete_backup(
    backup_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Elimina un respaldo específico del historial y almacenamiento."""
    if current_user.role != "administrador":
        raise ForbiddenException("Solo el administrador puede eliminar respaldos.")

    service = BackupService(db)
    success = service.delete_backup(backup_id)
    if not success:
        raise NotFoundException(f"Respaldo con ID {backup_id} no encontrado.")

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Eliminó el respaldo de seguridad con ID {backup_id}",
        module="seguridad",
    )

    return {"message": f"Copia de seguridad con ID {backup_id} eliminada exitosamente."}


@router.get("/config", summary="Consultar configuración de respaldos automáticos")
async def get_backup_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna la configuración actual de periodicidad automática y retención."""
    if current_user.role != "administrador":
        raise ForbiddenException("Solo el administrador puede consultar la configuración de respaldos.")

    service = BackupService(db)
    cfg = service.get_config()
    return {
        "auto_backup_enabled": cfg.auto_backup_enabled,
        "frequency_hours": cfg.frequency_hours,
        "retention_days": cfg.retention_days,
        "last_auto_backup": cfg.last_auto_backup,
        "updated_at": cfg.updated_at,
    }


@router.put("/config", summary="Actualizar configuración de respaldos automáticos")
async def update_backup_config(
    payload: BackupConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Guarda la configuración de respaldos automáticos en segundo plano."""
    if current_user.role != "administrador":
        raise ForbiddenException("Solo el administrador puede configurar los respaldos automáticos.")

    service = BackupService(db)
    cfg = service.update_config(
        auto_backup_enabled=payload.auto_backup_enabled,
        frequency_hours=payload.frequency_hours,
        retention_days=payload.retention_days,
    )

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Actualizó la configuración de respaldos automáticos (Activo: {cfg.auto_backup_enabled}, Cada {cfg.frequency_hours}h, Retención: {cfg.retention_days}d)",
        module="seguridad",
    )

    return {
        "auto_backup_enabled": cfg.auto_backup_enabled,
        "frequency_hours": cfg.frequency_hours,
        "retention_days": cfg.retention_days,
        "last_auto_backup": cfg.last_auto_backup,
        "mensaje": "Configuración de respaldos guardada exitosamente.",
    }


@router.post("/verificar", summary="Verificar integridad de copia de seguridad con SHA-256")
async def verify_backup_integrity(
    payload: BackupVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Comprueba que el hash SHA-256 del archivo coincida con el hash proporcionado o registrado."""
    if current_user.role != "administrador":
        raise ForbiddenException("Solo el administrador puede verificar respaldos.")

    service = BackupService(db)
    try:
        filename, content_bytes, registered_hash = service.get_backup_content(payload.id)
    except ValueError as e:
        raise NotFoundException(str(e))

    is_valid = service.verify_file_sha256(content_bytes, payload.expected_hash)

    return {
        "id": payload.id,
        "nombre_archivo": filename,
        "registrado_sha256": registered_hash,
        "comprobado_sha256": payload.expected_hash,
        "es_valido": is_valid,
        "mensaje": "Integridad criptográfica comprobada con éxito." if is_valid else "¡Alerta! El hash no coincide con el archivo.",
    }
