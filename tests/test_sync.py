"""Offline synchronization contract: idempotency, cash-only and stock safety."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.categoria import Categoria
from app.models.color import Color
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.reembolso_offline import ReembolsoOffline
from app.models.stock_inventario import StockInventario
from app.models.sucursal import Sucursal
from app.models.talla import Talla
from app.models.temporada import Temporada
from app.models.user import User


def _inventory(db, empresa_id: int, quantity: int = 3) -> StockInventario:
    suffix = uuid4().hex[:8]
    branch = Sucursal(
        empresa_id=empresa_id,
        name=f"Sync {suffix}", city="La Paz", address="Calle Sync 10", phone="70000123", active=True,
    )
    category = Categoria(empresa_id=empresa_id, nombre=f"Cat {suffix}")
    color = Color(empresa_id=empresa_id, nombre=f"Color {suffix}")
    size = Talla(empresa_id=empresa_id, nombre=f"T-{suffix}")
    season = Temporada(empresa_id=empresa_id, nombre=f"Temp {suffix}")
    db.add_all([branch, category, color, size, season])
    db.flush()
    product = Producto(
        empresa_id=empresa_id,
        codigo=f"SYNC-{suffix}", nombre="Prenda Sync", precio=Decimal("100.00"),
        categoria_id=category.id, temporada_id=season.id, active=True,
    )
    db.add(product)
    db.flush()
    product_color = ProductoColor(producto_codigo=product.codigo, color_id=color.id)
    db.add(product_color)
    db.flush()
    stock = StockInventario(
        sucursal_id=branch.id, producto_color_id=product_color.id, talla_id=size.id, cantidad=quantity,
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock


def test_cash_sale_sync_is_idempotent(client, db_session, admin_token):
    admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    stock = _inventory(db_session, admin.empresa_id)
    operation_uuid = str(uuid4())
    body = {
        "operation_uuid": operation_uuid,
        "operation_type": "venta_efectivo",
        "payload_version": 1,
        "client_created_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "codigo_cliente": "CLI-GENERAL",
            "sucursal_id": stock.sucursal_id,
            "metodo_pago": "efectivo",
            "efectivo_recibido": 120,
            "items": [{"stock_inventario_id": stock.id, "cantidad": 1}],
            "snapshot": {"total": 100},
        },
    }
    headers = {"Authorization": f"Bearer {admin_token}"}

    first = client.post("/api/v1/sync/operations", json=body, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "confirmada"
    result_id = first.json()["result_id"]

    second = client.post("/api/v1/sync/operations", json=body, headers=headers)
    assert second.status_code == 200, second.text
    assert second.json()["result_id"] == result_id
    db_session.refresh(stock)
    assert stock.cantidad == 2


def test_offline_qr_is_preserved_as_rejected(client, db_session, admin_token):
    admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    stock = _inventory(db_session, admin.empresa_id)
    operation_uuid = str(uuid4())
    body = {
        "operation_uuid": operation_uuid,
        "operation_type": "venta_efectivo",
        "payload_version": 1,
        "client_created_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "sucursal_id": stock.sucursal_id,
            "metodo_pago": "qr",
            "items": [{"stock_inventario_id": stock.id, "cantidad": 1}],
        },
    }
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post("/api/v1/sync/operations", json=body, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "rechazada"
    assert "solo acepta ventas en efectivo" in response.json()["reason"]
    db_session.refresh(stock)
    assert stock.cantidad == 3

    retry = client.post("/api/v1/sync/operations", json=body, headers=headers)
    assert retry.json()["status"] == "rechazada"


def test_reservation_sync_is_idempotent(client, db_session, admin_token):
    admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    stock = _inventory(db_session, admin.empresa_id)
    body = {
        "operation_uuid": str(uuid4()),
        "operation_type": "reserva",
        "payload_version": 1,
        "client_created_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "sucursal_id": stock.sucursal_id,
            "fecha_limite": (date.today() + timedelta(days=1)).isoformat(),
            "hora_retiro": "12:00:00",
            "items": [{"stock_inventario_id": stock.id, "cantidad": 1}],
        },
    }
    headers = {"Authorization": f"Bearer {admin_token}"}
    first = client.post("/api/v1/sync/operations", json=body, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "confirmada"
    second = client.post("/api/v1/sync/operations", json=body, headers=headers)
    assert second.json()["result_id"] == first.json()["result_id"]
    db_session.refresh(stock)
    assert stock.cantidad == 2


def test_last_unit_conflict_is_preserved_and_does_not_oversell(
    client, db_session, admin_token
):
    admin = db_session.query(User).filter(
        User.email == "admin_test@stylestore.com"
    ).one()
    stock = _inventory(db_session, admin.empresa_id, quantity=1)
    headers = {"Authorization": f"Bearer {admin_token}"}

    sale = client.post(
        "/api/v1/sync/operations",
        json={
            "operation_uuid": str(uuid4()),
            "operation_type": "venta_efectivo",
            "payload_version": 1,
            "client_created_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "sucursal_id": stock.sucursal_id,
                "metodo_pago": "efectivo",
                "efectivo_recibido": 100,
                "items": [{"stock_inventario_id": stock.id, "cantidad": 1}],
            },
        },
        headers=headers,
    )
    assert sale.status_code == 200, sale.text
    assert sale.json()["status"] == "confirmada"

    losing_operation = str(uuid4())
    reservation = client.post(
        "/api/v1/sync/operations",
        json={
            "operation_uuid": losing_operation,
            "operation_type": "reserva",
            "payload_version": 1,
            "client_created_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "sucursal_id": stock.sucursal_id,
                "fecha_limite": (date.today() + timedelta(days=1)).isoformat(),
                "hora_retiro": "12:00:00",
                "items": [{"stock_inventario_id": stock.id, "cantidad": 1}],
            },
        },
        headers=headers,
    )
    assert reservation.status_code == 200, reservation.text
    assert reservation.json()["status"] == "conflicto"
    assert "Stock insuficiente" in reservation.json()["reason"]

    retry = client.post(
        "/api/v1/sync/operations",
        json={
            "operation_uuid": losing_operation,
            "operation_type": "reserva",
            "payload_version": 1,
            "client_created_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "sucursal_id": stock.sucursal_id,
                "fecha_limite": (date.today() + timedelta(days=1)).isoformat(),
                "hora_retiro": "12:00:00",
                "items": [{"stock_inventario_id": stock.id, "cantidad": 1}],
            },
        },
        headers=headers,
    )
    assert retry.status_code == 200, retry.text
    assert retry.json()["status"] == "conflicto"
    assert retry.json()["reason"] == reservation.json()["reason"]

    db_session.refresh(stock)
    assert stock.cantidad == 0


def test_rejected_offline_cash_sale_creates_one_auditable_refund(
    client, db_session, admin_token
):
    admin = db_session.query(User).filter(
        User.email == "admin_test@stylestore.com"
    ).one()
    stock = _inventory(db_session, admin.empresa_id, quantity=0)
    operation_uuid = str(uuid4())
    headers = {"Authorization": f"Bearer {admin_token}"}
    body = {
        "operation_uuid": operation_uuid,
        "operation_type": "venta_efectivo",
        "payload_version": 1,
        "client_created_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "sucursal_id": stock.sucursal_id,
            "metodo_pago": "efectivo",
            "efectivo_recibido": 125,
            "items": [{"stock_inventario_id": stock.id, "cantidad": 1}],
            "snapshot": {"total": 125, "moneda": "BOB"},
        },
    }

    rejected = client.post("/api/v1/sync/operations", json=body, headers=headers)
    assert rejected.status_code == 200, rejected.text
    payload = rejected.json()
    assert payload["status"] == "conflicto"
    assert payload["refund_id"] is not None
    assert payload["refund_status"] == "pendiente"
    assert payload["refund_amount"] == 125

    replay = client.post("/api/v1/sync/operations", json=body, headers=headers)
    assert replay.status_code == 200, replay.text
    assert replay.json()["refund_id"] == payload["refund_id"]
    assert db_session.query(ReembolsoOffline).filter(
        ReembolsoOffline.operation_uuid == operation_uuid
    ).count() == 1

    mine = client.get("/api/v1/reembolsos/mios", headers=headers)
    assert mine.status_code == 200, mine.text
    assert any(item["id"] == payload["refund_id"] for item in mine.json())

    suffix = uuid4().hex[:8]
    other_email = f"refund-{suffix}@tenant.example.com"
    company = client.post(
        "/api/v1/empresas",
        json={
            "codigo": f"refund-{suffix}",
            "nombre": "Tenant ajeno al reembolso",
            "admin_email": other_email,
            "admin_name": "Admin ajeno",
            "admin_password": "TenantPass2026!",
        },
        headers=headers,
    )
    assert company.status_code == 201, company.text
    other_login = client.post(
        "/api/v1/auth/login",
        json={"email": other_email, "password": "TenantPass2026!"},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    assert client.get("/api/v1/reembolsos", headers=other_headers).json() == []
    cross_tenant = client.put(
        f"/api/v1/reembolsos/{payload['refund_id']}",
        json={"estado": "entregado", "observaciones": "Acceso de otro tenant"},
        headers=other_headers,
    )
    assert cross_tenant.status_code == 404

    delivered = client.put(
        f"/api/v1/reembolsos/{payload['refund_id']}",
        json={"estado": "entregado", "observaciones": "Efectivo devuelto al cliente"},
        headers=headers,
    )
    assert delivered.status_code == 200, delivered.text
    assert delivered.json()["estado"] == "entregado"
    assert delivered.json()["procesado_por"] == admin.id

    immutable = client.put(
        f"/api/v1/reembolsos/{payload['refund_id']}",
        json={"estado": "cancelado", "observaciones": "Intento de cambio posterior"},
        headers=headers,
    )
    assert immutable.status_code == 403
