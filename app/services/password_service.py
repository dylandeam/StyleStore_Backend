"""
Password Service for CU4 (request change with email confirmation).
"""
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.core.security import verify_password, hash_password
from app.core.exceptions import CredentialsException, InvalidOrExpiredTokenException
from app.core.email import send_password_change_email
from app.services.bitacora_service import BitacoraService


class PasswordService:
    """Service handling secure password change with one-time confirmation token."""

    def __init__(self, db: Session):
        self.db = db

    def request_password_change(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> dict:
        """
        Validate current password, generate single-use token, save pending hash, and send email.
        """
        # Validate current password
        if not verify_password(current_password, user.hashed_password):
            raise CredentialsException(detail="La contraseña actual es incorrecta.")

        # Generate unique token
        token = secrets.token_urlsafe(32)
        new_password_hash = hash_password(new_password)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        token_record = PasswordResetToken(
            user_id=user.id,
            token=token,
            new_password_hash=new_password_hash,
            expires_at=expires_at,
        )
        self.db.add(token_record)
        self.db.commit()

        # Build confirmation URL and send email
        confirm_url = f"{settings.FRONTEND_URL}/cuenta/confirmar-password?token={token}"
        send_password_change_email(to_email=user.email, confirm_url=confirm_url)

        # Log action to bitacora
        BitacoraService.registrar(
            db=self.db,
            user=user,
            action="Solicitó cambio de contraseña",
            module="auth",
        )

        return {
            "message": "Se ha enviado un enlace de confirmación a tu correo electrónico (válido por 15 minutos)."
        }

    def confirm_password_change(self, token: str) -> dict:
        """
        Validate token existence, expiration and single-use, then apply new password.
        """
        token_record = (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.token == token)
            .first()
        )

        if not token_record:
            raise InvalidOrExpiredTokenException("El enlace de confirmación no es válido o no existe.")

        if token_record.used_at is not None:
            raise InvalidOrExpiredTokenException("Este enlace de confirmación ya ha sido utilizado.")

        now_utc = datetime.now(timezone.utc)
        # Handle timezone-aware or naive datetime
        record_expires = token_record.expires_at
        if record_expires.tzinfo is None:
            record_expires = record_expires.replace(tzinfo=timezone.utc)

        if now_utc > record_expires:
            raise InvalidOrExpiredTokenException("El enlace de confirmación ha expirado (límite de 15 minutos).")

        # Apply new password
        user = self.db.query(User).filter(User.id == token_record.user_id).first()
        if not user:
            raise InvalidOrExpiredTokenException("El usuario asociado a este token ya no existe.")

        user.hashed_password = token_record.new_password_hash
        token_record.used_at = now_utc

        self.db.commit()

        # Log action to bitacora
        BitacoraService.registrar(
            db=self.db,
            user=user,
            action="Confirmó y actualizó su contraseña",
            module="auth",
        )

        return {
            "message": "Tu contraseña ha sido actualizada exitosamente. Ya puedes iniciar sesión con tu nueva clave."
        }
