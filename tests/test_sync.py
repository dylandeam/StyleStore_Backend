"""Offline synchronization contract: idempotency, cash-only and stock safety."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.categoria import Categoria
from app.models.color import Color
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.stock_inventario import StockInventario
from app.models.sucursal import Sucursal
from app.models.talla import Talla
from app.models.temporada import Temporada
from app.models.user import User


def _inventory(db, empresa_id: int) -> StockInventario:
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
        sucursal_id=branch.id, producto_color_id=product_color.id, talla_id=size.id, cantidad=3,
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
