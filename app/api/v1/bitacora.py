"""
Bitacora (Audit Log) endpoints (CU6).
Protegida con Llave Maestra / Contraseña de Administrador y registro de IP.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.bitacora import BitacoraPageResponse
from app.services.bitacora_service import BitacoraService
from app.core.security import verify_password, hash_password
from app.core.exceptions import BadRequestException, ForbiddenException
from app.config import settings

router = APIRouter(prefix="/bitacora", tags=["Bitacora / Auditoria"])


def get_client_ip(request: Request) -> str:
    """Extrae la dirección IP real del cliente que realiza la petición."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


@router.get(
    "",
    response_model=BitacoraPageResponse,
    summary="Visualizar bitácora",
    description="Obtiene los registros de auditoría del sistema con trazabilidad de IP, ordenados descendentemente.",
)
async def list_bitacora(
    user: str | None = Query(None, description="Filtrar por nombre o correo de usuario"),
    from_date: datetime | None = Query(None, alias="from", description="Fecha inicial"),
    to_date: datetime | None = Query(None, alias="to", description="Fecha final"),
    module: str | None = Query(None, description="Módulo filtrado"),
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Cantidad de registros por página"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Listar registros de auditoría filtrados y paginados."""
    service = BitacoraService()
    return service.list_logs(
        db=db,
        user_query=user,
        from_date=from_date,
        to_date=to_date,
        module=module,
        page=page,
        size=size,
    )


class MasterKeyVerifyRequest(BaseModel):
    key: str = Field(..., min_length=1, description="Llave maestra o contraseña de bitácora")


@router.post("/verificar-llave", summary="Verificar llave maestra para desbloqueo de bitácora")
async def verify_master_key(
    payload: MasterKeyVerifyRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verifica la contraseña de acceso para desbloquear la bitácora:
    1. Si el administrador definió una clave personalizada para bitácora, valida contra ella.
    2. Por defecto, valida contra la misma contraseña de su cuenta de usuario.
    3. Permite la llave maestra global de entorno ADMIN_MASTER_KEY.
    4. Registra en la bitácora el evento con la dirección IP del solicitante.
    """
    ip = get_client_ip(request)
    input_key = payload.key.strip()
    is_valid = False

    # 1. Verificar contra la clave configurada del usuario actual
    if current_user.bitacora_password_hash:
        if verify_password(input_key, current_user.bitacora_password_hash):
            is_valid = True
    else:
        # Predeterminada: misma contraseña de su cuenta
        if verify_password(input_key, current_user.hashed_password):
            is_valid = True

    # 2. Verificar contra la llave maestra del servidor
    if not is_valid and input_key == settings.ADMIN_MASTER_KEY:
        is_valid = True

    # 3. Si el usuario actual no es admin (ej. empleado probando con clave del admin de la tienda)
    if not is_valid:
        admins = db.query(User).filter(User.role == "administrador", User.is_active.is_(True)).all()
        for adm in admins:
            target_hash = adm.bitacora_password_hash or adm.hashed_password
            if target_hash and verify_password(input_key, target_hash):
                is_valid = True
                break

    if is_valid:
        BitacoraService.registrar(
            db=db,
            user=current_user,
            action=f"Desbloqueó acceso a la bitácora de auditoría",
            module="seguridad",
            ip_address=ip,
        )
        return {
            "valid": True,
            "message": "Acceso a la bitácora desbloqueado con éxito.",
            "ip": ip,
        }

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Intento fallido de desbloqueo de bitácora",
        module="seguridad",
        ip_address=ip,
    )
    return {
        "valid": False,
        "message": "Contraseña de bitácora o llave maestra incorrecta.",
        "ip": ip,
    }


class CambiarClaveBitacoraRequest(BaseModel):
    current_password: str = Field(..., description="Contraseña actual de la cuenta del administrador")
    new_bitacora_password: str = Field(..., min_length=4, description="Nueva contraseña personalizada para la bitácora")


@router.put("/cambiar-clave", summary="Cambiar contraseña de seguridad de la bitácora")
async def change_bitacora_password(
    payload: CambiarClaveBitacoraRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permite al administrador cambiar la contraseña de acceso a la bitácora.
    Verifica obligatoriamente su contraseña actual de cuenta antes de realizar el cambio.
    """
    if current_user.role != "administrador":
        raise ForbiddenException("Solo el administrador puede configurar la contraseña de la bitácora.")

    # Verificar contraseña actual de la cuenta
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise BadRequestException("La contraseña actual de tu cuenta es incorrecta.")

    current_user.bitacora_password_hash = hash_password(payload.new_bitacora_password)
    db.commit()

    ip = get_client_ip(request)
    BitacoraService.registrar(
        db=db,
        user=current_user,
        action="El administrador actualizó la contraseña de seguridad de la bitácora",
        module="seguridad",
        ip_address=ip,
    )
    return {"message": "Contraseña de la bitácora actualizada exitosamente."}


class RestablecerClaveBitacoraRequest(BaseModel):
    current_password: str = Field(..., description="Contraseña actual de la cuenta")


@router.post("/restablecer-clave", summary="Restablecer clave de bitácora a la predeterminada (cuenta)")
async def reset_bitacora_password(
    payload: RestablecerClaveBitacoraRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Restablece la contraseña de la bitácora para que vuelva a ser idéntica a la contraseña de la cuenta.
    """
    if current_user.role != "administrador":
        raise ForbiddenException("Solo el administrador puede restablecer la clave de la bitácora.")

    if not verify_password(payload.current_password, current_user.hashed_password):
        raise BadRequestException("La contraseña actual de tu cuenta es incorrecta.")

    current_user.bitacora_password_hash = None
    db.commit()

    ip = get_client_ip(request)
    BitacoraService.registrar(
        db=db,
        user=current_user,
        action="Restableció la clave de bitácora a la contraseña predeterminada de su cuenta",
        module="seguridad",
        ip_address=ip,
    )
    return {"message": "La contraseña de la bitácora ha sido restablecida a la contraseña de tu cuenta."}


@router.get("/estado-clave", summary="Consultar si la clave de bitácora está personalizada")
async def get_bitacora_key_status(
    current_user: User = Depends(get_current_user),
):
    """Indica si el usuario tiene una contraseña de bitácora personalizada o la predeterminada."""
    is_custom = bool(current_user.bitacora_password_hash)
    return {
        "is_custom": is_custom,
        "type": "personalizada" if is_custom else "predeterminada (contraseña de tu cuenta)",
    }
