"""Campaign scheduling, targeting and tenant-boundary regression tests."""
from datetime import datetime, timedelta, timezone

from app.core.security import create_access_token, hash_password
from app.models.empresa import Empresa
from app.models.notificacion import CampanaNotificacion, Notificacion
from app.models.user import User


def _token(user: User) -> str:
    return create_access_token(data={
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "empresa_id": user.empresa_id,
    })


def _tenant_users(db_session):
    empresa = db_session.query(Empresa).filter(Empresa.codigo == "stylestore").one()
    admin = User(
        empresa_id=empresa.id,
        email="campaign-admin@example.com",
        name="Campaign Admin",
        hashed_password=hash_password("Test1234!"),
        role="administrador",
        is_active=True,
    )
    client = User(
        empresa_id=empresa.id,
        email="campaign-client@example.com",
        name="Campaign Client",
        hashed_password=hash_password("Test1234!"),
        role="cliente",
        is_active=True,
    )
    db_session.add_all([admin, client])
    db_session.commit()
    return empresa, admin, client


def test_tenant_admin_can_send_personalized_campaign_only_to_selected_user(
    client, db_session, monkeypatch
):
    _, admin, target = _tenant_users(db_session)
    monkeypatch.setattr("app.services.notificacion_service.send_notification_email", lambda **_: True)
    monkeypatch.setattr(
        "app.services.push_notification_service.PushNotificationService.send_to_user",
        classmethod(lambda cls, db, **kwargs: 1),
    )

    response = client.post(
        "/api/v1/notificaciones/campanas",
        headers={"Authorization": f"Bearer {_token(admin)}"},
        json={
            "titulo": "Oferta personal",
            "mensaje": "Esta selección puede interesarte",
            "audiencia": "usuarios_seleccionados",
            "target_user_ids": [target.id],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["estado"] == "completada"
    delivered = db_session.query(Notificacion).filter(
        Notificacion.titulo == "Oferta personal"
    ).all()
    assert [(item.user_id, item.empresa_id) for item in delivered] == [
        (target.id, target.empresa_id)
    ]


def test_recurring_campaign_is_persisted_and_can_be_cancelled(
    client, db_session
):
    _, admin, _ = _tenant_users(db_session)
    scheduled = datetime.now(timezone.utc) + timedelta(days=1)
    response = client.post(
        "/api/v1/notificaciones/campanas",
        headers={"Authorization": f"Bearer {_token(admin)}"},
        json={
            "titulo": "Novedad recurrente",
            "mensaje": "Hay una ropa que puede interesarte",
            "audiencia": "clientes",
            "programada_para": scheduled.isoformat(),
            "recurrencia_dias": 3,
        },
    )
    assert response.status_code == 200, response.text
    campaign_id = response.json()["id"]
    assert response.json()["estado"] == "programada"
    campaign = db_session.get(CampanaNotificacion, campaign_id)
    assert campaign.recurrencia_dias == 3

    cancelled = client.post(
        f"/api/v1/notificaciones/campanas/{campaign_id}/cancelar",
        headers={"Authorization": f"Bearer {_token(admin)}"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["estado"] == "cancelada"


def test_tenant_admin_can_target_employees_without_notifying_clients(client, db_session):
    empresa, admin, customer = _tenant_users(db_session)
    employee = User(
        empresa_id=empresa.id,
        email="campaign-employee@example.com",
        name="Campaign Employee",
        hashed_password=hash_password("Test1234!"),
        role="cajero",
        is_active=True,
    )
    db_session.add(employee)
    db_session.commit()
    response = client.post(
        "/api/v1/notificaciones/campanas",
        headers={"Authorization": f"Bearer {_token(admin)}"},
        json={
            "titulo": "Aviso interno",
            "mensaje": "Reunión de personal",
            "audiencia": "empleados",
        },
    )
    assert response.status_code == 200, response.text
    delivered_ids = {
        item.user_id for item in db_session.query(Notificacion).filter(
            Notificacion.titulo == "Aviso interno"
        ).all()
    }
    assert employee.id in delivered_ids
    assert customer.id not in delivered_ids
    assert admin.id not in delivered_ids
