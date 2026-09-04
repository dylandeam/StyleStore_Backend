"""
Password management endpoints (CU4).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.password import (
    RequestPasswordChangeRequest,
    ConfirmPasswordChangeRequest,
)
from app.schemas.common import MessageResponse
from app.services.password_service import PasswordService

router = APIRouter(prefix="/password", tags=["Password"])


@router.post(
    "/request-change",
    response_model=MessageResponse,
    summary="Solicitar cambio de contraseña",
    description="Valida la contraseña actual y envía un correo con enlace de confirmación válido por 15 minutos.",
)
async def request_password_change(
    request: RequestPasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Solicita un cambio de contraseña y envía el correo con token."""
    password_service = PasswordService(db)
    result = password_service.request_password_change(
        user=current_user,
        current_password=request.current_password,
        new_password=request.new_password,
    )
    return MessageResponse(message=result["message"])


@router.post(
    "/confirm",
    response_model=MessageResponse,
    summary="Confirmar cambio de contraseña",
    description="Valida el token de un solo uso recibido por correo y actualiza la contraseña del usuario.",
)
async def confirm_password_change(
    request: ConfirmPasswordChangeRequest,
    db: Session = Depends(get_db),
):
    """Aplica la nueva contraseña validando el token de confirmación."""
    password_service = PasswordService(db)
    result = password_service.confirm_password_change(token=request.token)
    return MessageResponse(message=result["message"])
