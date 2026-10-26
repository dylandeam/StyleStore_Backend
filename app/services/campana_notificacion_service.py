"""Campañas de notificaciones multitenant, programadas e idempotentes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.notificacion import CampanaNotificacion, EntregaCampanaNotificacion
from app.models.user import User
from app.models.user_empresa import UserEmpresa
from app.services.notificacion_service import NotificacionService


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class CampanaNotificacionService:
    def __init__(self, db: Session):
        self.db = db

    def _tenant_users(self, empresa_id: int):
        member_ids = self.db.query(UserEmpresa.user_id).filter(
            UserEmpresa.empresa_id == empresa_id,
            UserEmpresa.active.is_(True),
        )
        return self.db.query(User).filter(
            User.is_active.is_(True),
            User.is_platform_admin.is_(False),
            or_(User.empresa_id == empresa_id, User.id.in_(member_ids)),
        )

    def resolve_targets(self, campaign: CampanaNotificacion) -> list[tuple[User, int]]:
        targets: list[tuple[User, int]] = []
        if campaign.empresa_id is None:
            tenant_ids = [int(item) for item in (campaign.target_empresa_ids or [])]
            if not tenant_ids:
                tenant_ids = [row[0] for row in self.db.query(Empresa.id).all()]
            for empresa_id in tenant_ids:
                admins = self._tenant_users(empresa_id).filter(User.role == "administrador").all()
                targets.extend((user, empresa_id) for user in admins)
        else:
            query = self._tenant_users(campaign.empresa_id)
            if campaign.audiencia == "clientes":
                query = query.filter(User.role == "cliente")
            elif campaign.audiencia == "empleados":
                query = query.filter(User.role.notin_(["cliente", "administrador"]))
            elif campaign.audiencia == "administradores":
                query = query.filter(User.role == "administrador")
            elif campaign.audiencia == "usuarios_seleccionados":
                selected = [int(item) for item in (campaign.target_user_ids or [])]
                query = query.filter(User.id.in_(selected)) if selected else query.filter(False)
            targets.extend((user, campaign.empresa_id) for user in query.all())

        unique: dict[tuple[int, int], tuple[User, int]] = {}
        for user, empresa_id in targets:
            unique[(user.id, empresa_id)] = (user, empresa_id)
        return list(unique.values())

    def dispatch(self, campaign: CampanaNotificacion) -> CampanaNotificacion:
        if campaign.estado == "cancelada":
            return campaign
        occurrence = as_utc(campaign.proxima_ejecucion)
        campaign.estado = "procesando"
        self.db.commit()

        targets = self.resolve_targets(campaign)
        campaign.total_destinatarios = len(targets)
        sent = 0
        notifier = NotificacionService(self.db)
        for user, empresa_id in targets:
            already_sent = self.db.query(EntregaCampanaNotificacion.id).filter(
                EntregaCampanaNotificacion.campana_id == campaign.id,
                EntregaCampanaNotificacion.user_id == user.id,
                EntregaCampanaNotificacion.empresa_id == empresa_id,
                EntregaCampanaNotificacion.ejecucion_programada == occurrence,
            ).first()
            if already_sent:
                continue
            notifier.crear_notificacion(
                user_id=user.id,
                empresa_id=empresa_id,
                tipo="campana",
                titulo=campaign.titulo,
                mensaje=campaign.mensaje,
                url_accion=campaign.url_accion,
                enviar_email=campaign.enviar_email,
            )
            self.db.add(EntregaCampanaNotificacion(
                campana_id=campaign.id,
                user_id=user.id,
                empresa_id=empresa_id,
                ejecucion_programada=occurrence,
            ))
            self.db.commit()
            sent += 1

        campaign.total_enviados += sent
        campaign.ultima_ejecucion = utcnow()
        if campaign.recurrencia_dias:
            next_run = occurrence + timedelta(days=campaign.recurrencia_dias)
            now = utcnow()
            while next_run <= now:
                next_run += timedelta(days=campaign.recurrencia_dias)
            campaign.proxima_ejecucion = next_run
            campaign.estado = "activa"
        else:
            campaign.estado = "completada"
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def dispatch_due(self) -> int:
        now = utcnow()
        campaigns = self.db.query(CampanaNotificacion).filter(
            CampanaNotificacion.estado.in_(["programada", "activa"]),
            CampanaNotificacion.proxima_ejecucion <= now,
        ).order_by(CampanaNotificacion.proxima_ejecucion).limit(20).all()
        completed = 0
        for campaign in campaigns:
            try:
                self.dispatch(campaign)
                completed += 1
            except Exception:
                self.db.rollback()
                failed = self.db.get(CampanaNotificacion, campaign.id)
                if failed:
                    failed.estado = "fallida"
                    self.db.commit()
        return completed

    @staticmethod
    def serialize(campaign: CampanaNotificacion) -> dict:
        return {
            "id": campaign.id,
            "empresa_id": campaign.empresa_id,
            "created_by_id": campaign.created_by_id,
            "titulo": campaign.titulo,
            "mensaje": campaign.mensaje,
            "url_accion": campaign.url_accion,
            "audiencia": campaign.audiencia,
            "target_user_ids": campaign.target_user_ids or [],
            "target_empresa_ids": campaign.target_empresa_ids or [],
            "enviar_email": campaign.enviar_email,
            "recurrencia_dias": campaign.recurrencia_dias,
            "proxima_ejecucion": campaign.proxima_ejecucion.isoformat(),
            "estado": campaign.estado,
            "total_destinatarios": campaign.total_destinatarios,
            "total_enviados": campaign.total_enviados,
            "ultima_ejecucion": campaign.ultima_ejecucion.isoformat() if campaign.ultima_ejecucion else None,
            "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        }
