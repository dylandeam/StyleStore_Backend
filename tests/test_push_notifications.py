"""Push registration and tenant isolation regression tests."""
from decimal import Decimal

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


def test_online_sale_notifies_only_active_staff_from_order_tenant(
    db_session, monkeypatch
):
    from app.models.empresa import Empresa
    from app.models.orden_venta import OrdenVenta
    from app.models.sucursal import Sucursal
    from app.models.user import User
    from app.services.notificacion_service import NotificacionService
    from app.services.push_notification_service import PushNotificationService

    tenant = db_session.query(Empresa).filter(Empresa.codigo == "stylestore").one()
    other_tenant = Empresa(codigo="other-push", nombre="Other Push Tenant", active=True)
    db_session.add(other_tenant)
    db_session.flush()

    branch = Sucursal(
        empresa_id=tenant.id,
        name="Sucursal Notificaciones",
        city="Santa Cruz",
        address="Av. Prueba 123",
        phone="70000001",
        active=True,
    )
    users = [
        User(
            empresa_id=tenant.id,
            email="staff-sale@stylestore.test",
            name="Staff",
            apellido="Ventas",
            hashed_password="test",
            role="empleado",
            is_active=True,
        ),
        User(
            empresa_id=tenant.id,
            email="tenant-admin-sale@stylestore.test",
            name="Admin",
            apellido="Tenant",
            hashed_password="test",
            role="administrador",
            is_active=True,
        ),
        User(
            empresa_id=tenant.id,
            email="client-sale@stylestore.test",
            name="Cliente",
            apellido="Excluido",
            hashed_password="test",
            role="cliente",
            is_active=True,
        ),
        User(
            empresa_id=tenant.id,
            email="inactive-sale@stylestore.test",
            name="Inactivo",
            apellido="Excluido",
            hashed_password="test",
            role="empleado",
            is_active=False,
        ),
        User(
            empresa_id=other_tenant.id,
            email="other-staff-sale@stylestore.test",
            name="Otro",
            apellido="Tenant",
            hashed_password="test",
            role="empleado",
            is_active=True,
        ),
    ]
    db_session.add(branch)
    db_session.add_all(users)
    db_session.flush()
    order = OrdenVenta(
        estado="pendiente_pago",
        total=Decimal("149.90"),
        tipo_venta="en linea",
        comprador_nombre="Cliente de prueba",
        sucursal_id=branch.id,
        metodo_pago="PAYPAL",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    pushed_to = []

    def fake_send(cls, db, **kwargs):
        pushed_to.append((kwargs["user_id"], kwargs["empresa_id"], kwargs["data"]["type"]))
        return 1

    monkeypatch.setattr(PushNotificationService, "send_to_user", classmethod(fake_send))

    service = NotificacionService(db_session)
    assert service.notificar_nueva_venta_online(order) == 2
    assert service.notificar_nueva_venta_online(order) == 0

    expected_ids = {users[0].id, users[1].id}
    notifications = db_session.query(Notificacion).filter(
        Notificacion.tipo == "nueva_venta_online"
    ).all()
    assert {item.user_id for item in notifications} == expected_ids
    assert all(item.empresa_id == tenant.id for item in notifications)
    assert all(item.url_accion == f"/admin/ventas?orden_id={order.id}" for item in notifications)
    assert {user_id for user_id, _, _ in pushed_to} == expected_ids
    assert all(company_id == tenant.id for _, company_id, _ in pushed_to)
    assert all(kind == "nueva_venta_online" for _, _, kind in pushed_to)
