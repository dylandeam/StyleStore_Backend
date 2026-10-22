"""Tests for sync metrics, diagnostics (REQ-070), and uniform out-of-stock messages (REQ-066)."""
from datetime import datetime, timezone
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


def _seed_stock(db, empresa_id: int, quantity: int = 1) -> StockInventario:
    suffix = uuid4().hex[:8]
    branch = Sucursal(
        empresa_id=empresa_id,
        name=f"Suc {suffix}",
        city="La Paz",
        address="Calle Central",
        phone="70000000",
        active=True,
    )
    cat = Categoria(empresa_id=empresa_id, nombre=f"Cat {suffix}")
    col = Color(empresa_id=empresa_id, nombre=f"Col {suffix}")
    sz = Talla(empresa_id=empresa_id, nombre=f"T-{suffix}")
    temp = Temporada(empresa_id=empresa_id, nombre=f"Temp {suffix}")
    db.add_all([branch, cat, col, sz, temp])
    db.flush()

    prod = Producto(
        empresa_id=empresa_id,
        codigo=f"PRD-{suffix}",
        nombre=f"Prenda Test {suffix}",
        precio=Decimal("80.00"),
        categoria_id=cat.id,
        temporada_id=temp.id,
        active=True,
    )
    db.add(prod)
    db.flush()

    prod_col = ProductoColor(producto_codigo=prod.codigo, color_id=col.id)
    db.add(prod_col)
    db.flush()

    stock = StockInventario(
        sucursal_id=branch.id,
        producto_color_id=prod_col.id,
        talla_id=sz.id,
        cantidad=quantity,
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock


def test_uniform_prenda_no_disponible_message(client, db_session, admin_token):
    admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    stock = _seed_stock(db_session, admin.empresa_id, quantity=0)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Presencial out-of-stock should say "Prenda no disponible"
    resp_presencial = client.post(
        "/api/v1/ventas/presencial",
        json={
            "comprador_nombre": "Cliente Mostrador",
            "comprador_ci": "1234567",
            "sucursal_id": stock.sucursal_id,
            "metodo_pago": "efectivo",
            "efectivo_recibido": 100,
            "items": [{"stock_inventario_id": stock.id, "cantidad": 1}],
        },
        headers=headers,
    )
    assert resp_presencial.status_code == 400
    assert "Prenda no disponible" in resp_presencial.json()["detail"]


def test_sync_metrics_and_diagnostics_aggregation(client, db_session, admin_token):
    admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    stock_ok = _seed_stock(db_session, admin.empresa_id, quantity=5)
    stock_empty = _seed_stock(db_session, admin.empresa_id, quantity=0)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create a successful sync operation
    op1_uuid = str(uuid4())
    resp1 = client.post(
        "/api/v1/sync/operations",
        json={
            "operation_uuid": op1_uuid,
            "operation_type": "venta_efectivo",
            "payload_version": 1,
            "client_created_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "sucursal_id": stock_ok.sucursal_id,
                "metodo_pago": "efectivo",
                "efectivo_recibido": 100,
                "items": [{"stock_inventario_id": stock_ok.id, "cantidad": 1}],
                "snapshot": {"total": 80},
            },
        },
        headers=headers,
    )
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "confirmada"

    # 2. Create a conflicting sync operation (0 stock -> conflict + refund)
    op2_uuid = str(uuid4())
    resp2 = client.post(
        "/api/v1/sync/operations",
        json={
            "operation_uuid": op2_uuid,
            "operation_type": "venta_efectivo",
            "payload_version": 1,
            "client_created_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "sucursal_id": stock_empty.sucursal_id,
                "metodo_pago": "efectivo",
                "efectivo_recibido": 80,
                "items": [{"stock_inventario_id": stock_empty.id, "cantidad": 1}],
                "snapshot": {"total": 80, "moneda": "BOB"},
            },
        },
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "conflicto"

    # 3. Query sync metrics endpoint (REQ-070)
    metrics_resp = client.get("/api/v1/sync/metricas", headers=headers)
    assert metrics_resp.status_code == 200, metrics_resp.text
    data = metrics_resp.json()

    assert data["empresa_id"] == admin.empresa_id
    assert data["total_operaciones"] >= 2
    assert data["total_confirmadas"] >= 1
    assert data["total_conflictos"] >= 1
    assert 0.0 <= data["tasa_exito_porcentaje"] <= 100.0
    assert "venta_efectivo" in data["operaciones_por_tipo"]
    assert "reembolsos_asociados" in data
    assert data["reembolsos_asociados"]["total_reembolsos"] >= 1

    # Verify diagnostic item structure
    diagnostics = data["conflictos_recientes"]
    assert isinstance(diagnostics, list)
    assert len(diagnostics) >= 1
    found_conflict = next((d for d in diagnostics if d["operation_uuid"] == op2_uuid), None)
    assert found_conflict is not None
    assert found_conflict["status"] == "conflicto"
    assert "stock" in found_conflict["reason"].lower() or "disponib" in found_conflict["reason"].lower()
    assert found_conflict["refund_id"] is not None
