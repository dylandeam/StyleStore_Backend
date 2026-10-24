"""Push registration and tenant isolation regression tests."""
from app.models.notificacion import Notificacion, PushDevice


def test_register_and_unregister_push_device(client, db_session, admin_token):
    token = "fcm-test-token-" + ("x" * 64)
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = client.post(
        "/api/v1/notificaciones/dispositivos",
        headers=headers,
        json={"token": token, "platform": "android", "device_id": "test-phone"},
    )
    assert response.status_code == 200
    device = db_session.query(PushDevice).filter(PushDevice.token == token).one()
    assert device.active is True
    assert device.empresa_id is not None

    response = client.request(
        "DELETE",
        "/api/v1/notificaciones/dispositivos",
        headers=headers,
        json={"token": token},
    )
    assert response.status_code == 200
    db_session.refresh(device)
    assert device.active is False


def test_notification_list_is_scoped_to_active_tenant(client, db_session, admin_token):
    from app.models.user import User

    user = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    own = Notificacion(
        empresa_id=user.empresa_id,
        user_id=user.id,
        tipo="general",
        titulo="Visible",
        mensaje="Pertenece al tenant activo",
    )
    db_session.add(own)
    db_session.commit()

    response = client.get(
        "/api/v1/notificaciones/mis-notificaciones",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert [item["titulo"] for item in response.json()["items"]] == ["Visible"]


def test_push_self_test_uses_current_user_and_tenant(
    client, db_session, admin_token, monkeypatch
):
    from app.models.user import User
    from app.services.push_notification_service import PushNotificationService

    current_user = db_session.query(User).filter(
        User.email == "admin_test@stylestore.com"
    ).one()
    captured = {}

    def fake_send(cls, db, **kwargs):
        captured.update(kwargs)
        return 1

    monkeypatch.setattr(PushNotificationService, "send_to_user", classmethod(fake_send))

    response = client.post(
        "/api/v1/notificaciones/prueba-push",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    assert response.json()["sent"] == 1
    assert captured["user_id"] == current_user.id
    assert captured["empresa_id"] == current_user.empresa_id
    assert captured["data"]["type"] == "push_test"
