"""Firebase Cloud Messaging delivery with safe optional configuration."""
from __future__ import annotations

import base64
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.notificacion import PushDevice


logger = logging.getLogger("push_notifications")


class PushNotificationService:
    """Registers installations and sends tenant-scoped FCM notifications."""

    _firebase_app: Any = None
    _initialization_attempted = False

    @classmethod
    def _get_firebase_app(cls):
        if cls._initialization_attempted:
            return cls._firebase_app
        cls._initialization_attempted = True
        raw = settings.FIREBASE_SERVICE_ACCOUNT_JSON.strip()
        if not raw and settings.FIREBASE_SERVICE_ACCOUNT_B64.strip():
            try:
                raw = base64.b64decode(settings.FIREBASE_SERVICE_ACCOUNT_B64).decode("utf-8")
            except Exception:
                logger.exception("Invalid FIREBASE_SERVICE_ACCOUNT_B64; push delivery disabled")
                return None
        if not raw:
            logger.info("Firebase credentials are not configured; push delivery is disabled")
            return None
        try:
            import firebase_admin
            from firebase_admin import credentials

            try:
                cls._firebase_app = firebase_admin.get_app()
            except ValueError:
                cls._firebase_app = firebase_admin.initialize_app(
                    credentials.Certificate(json.loads(raw))
                )
        except Exception:
            logger.exception("Firebase initialization failed; in-app notifications remain available")
        return cls._firebase_app

    @staticmethod
    def register_device(
        db: Session,
        *,
        user_id: int,
        empresa_id: int,
        token: str,
        platform: str,
        device_id: str | None = None,
    ) -> PushDevice:
        device = db.query(PushDevice).filter(PushDevice.token == token).first()
        if device is None:
            device = PushDevice(token=token, user_id=user_id, empresa_id=empresa_id)
            db.add(device)
        device.user_id = user_id
        device.empresa_id = empresa_id
        device.platform = platform
        device.device_id = device_id
        device.active = True
        db.commit()
        db.refresh(device)
        return device

    @staticmethod
    def unregister_device(db: Session, *, user_id: int, token: str) -> bool:
        device = db.query(PushDevice).filter(
            PushDevice.user_id == user_id,
            PushDevice.token == token,
        ).first()
        if device is None:
            return False
        device.active = False
        db.commit()
        return True

    @classmethod
    def send_to_user(
        cls,
        db: Session,
        *,
        user_id: int,
        empresa_id: int,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> int:
        app = cls._get_firebase_app()
        if app is None:
            return 0
        devices = db.query(PushDevice).filter(
            PushDevice.user_id == user_id,
            PushDevice.empresa_id == empresa_id,
            PushDevice.active.is_(True),
        ).all()
        if not devices:
            return 0

        from firebase_admin import messaging

        sent = 0
        payload = {key: str(value) for key, value in (data or {}).items()}
        for device in devices:
            try:
                messaging.send(
                    messaging.Message(
                        token=device.token,
                        notification=messaging.Notification(title=title, body=body),
                        data=payload,
                        android=messaging.AndroidConfig(
                            priority="high",
                            notification=messaging.AndroidNotification(
                                channel_id="stylestore_alerts",
                                sound="default",
                            ),
                        ),
                        apns=messaging.APNSConfig(
                            payload=messaging.APNSPayload(
                                aps=messaging.Aps(sound="default", badge=1)
                            )
                        ),
                    ),
                    app=app,
                )
                sent += 1
            except Exception as exc:
                # Invalid/expired tokens should not be retried indefinitely.
                if exc.__class__.__name__ in {"UnregisteredError", "SenderIdMismatchError"}:
                    device.active = False
                logger.warning("FCM delivery failed for device %s: %s", device.id, exc)
        db.commit()
        return sent
