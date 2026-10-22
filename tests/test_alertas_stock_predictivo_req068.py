"""
Pruebas automatizadas para REQ-068:
Funcionalidad propuesta por el equipo: Alerta predictiva de agotamiento de stock,
estimación de cobertura en días, criticidad, reposición sugerida y exportación.
"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.models.empresa import Empresa
from app.models.sucursal import Sucursal
from app.models.user import User
from app.models.categoria import Categoria
from app.models.temporada import Temporada
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.color import Color
from app.models.talla import Talla
from app.models.stock_inventario import StockInventario
from app.models.orden_venta import OrdenVenta, DetalleVenta
from app.services.plan_service import PlanService


def _headers(user: User) -> dict:
    tok = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
    return {"Authorization": f"Bearer {tok}"}


def _setup_tenant(db, suffix: str):
    empresa = Empresa(nombre=f"Empresa Alert {suffix}", codigo=f"alt-{suffix}", active=True)
    db.add(empresa)
    db.commit()

    sucursal = Sucursal(
        empresa_id=empresa.id,
        name=f"Sucursal Alert {suffix}",
        city="La Paz",
        address="Calle Calacoto 10",
        phone="76543210",
        active=True,
    )
    db.add(sucursal)
    db.commit()

    user = User(
        email=f"manager_{suffix}@alert.com",
        name="Gerente",
        apellido="Stock",
        role="administrador",
        empresa_id=empresa.id,
        is_active=True,
        hashed_password=hash_password("admin1234"),
    )
    db.add(user)
    db.commit()

    PlanService(db).contract(user, "profesional")
    db.commit()
    return empresa, sucursal, user


def _seed_product_and_stock(db, empresa_id: int, sucursal_id: int, suffix: str, quantity: int = 5):
    cat = Categoria(empresa_id=empresa_id, nombre=f"Cat-{suffix}")
    temp = Temporada(empresa_id=empresa_id, nombre=f"Temp-{suffix}")
    col = Color(empresa_id=empresa_id, nombre=f"Azul-{suffix}")
    sz = Talla(empresa_id=empresa_id, nombre=f"M-{suffix}")
    db.add_all([cat, temp, col, sz])
    db.flush()

    prod = Producto(
        empresa_id=empresa_id,
        codigo=f"PRD-{suffix}",
        nombre=f"Vestido Elegante {suffix}",
        precio=Decimal("280.00"),
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
        sucursal_id=sucursal_id,
        producto_color_id=prod_col.id,
        talla_id=sz.id,
        cantidad=quantity,
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock, prod


def test_alertas_stock_predictivo_calculo_y_aislamiento(client: TestClient, db_session):
    """
    REQ-068: Valida el cálculo de velocidad de venta diaria, días de cobertura,
    categorización de criticidad y estricto aislamiento por tenant.
    """
    db = db_session
    suffix1 = uuid4().hex[:6]
    suffix2 = uuid4().hex[:6]

    # Tenant 1: Con ventas y riesgo de agotamiento
    empresa1, sucursal1, user1 = _setup_tenant(db, suffix1)
    stock1, prod1 = _seed_product_and_stock(db, empresa1.id, sucursal1.id, suffix1, quantity=4)

    # Registrar orden de venta reciente para stock1 (6 unidades en los últimos 10 días -> velocidad 6/30 = 0.20/día)
    orden = OrdenVenta(
        fecha=date.today() - timedelta(days=5),
        estado="pagada",
        total=Decimal("1680.00"),
        tipo_venta="presencial",
        sucursal_id=sucursal1.id,
    )
    db.add(orden)
    db.flush()

    detalle = DetalleVenta(
        orden_venta_id=orden.id,
        stock_inventario_id=stock1.id,
        producto_nombre=prod1.nombre,
        cantidad=6,
        precio_unitario=Decimal("280.00"),
        subtotal=Decimal("1680.00"),
    )
    db.add(detalle)
    db.commit()

    # Tenant 2: Otro tenant aislado con stock en 0
    empresa2, sucursal2, user2 = _setup_tenant(db, suffix2)
    stock2, prod2 = _seed_product_and_stock(db, empresa2.id, sucursal2.id, suffix2, quantity=0)

    # 1. Consultar alertas para Tenant 1
    resp1 = client.get("/api/v1/reportes/alertas-stock-predictivo", headers=_headers(user1))
    assert resp1.status_code == 200, resp1.text
    data1 = resp1.json()

    assert data1["tenant_id"] == empresa1.id
    assert data1["total_items_evaluados"] == 1
    # Stock 1 debe estar presente en items de Tenant 1
    item = data1["items"][0]
    assert item["stock_id"] == stock1.id
    assert item["stock_actual"] == 4
    assert item["velocidad_diaria"] == 0.20
    # Cobertura esperada: 4 / 0.20 = 20.0 días
    assert item["dias_cobertura"] == 20.0

    # 2. Consultar alertas para Tenant 2 (Stock en 0 -> debe ser CRITICO)
    resp2 = client.get("/api/v1/reportes/alertas-stock-predictivo", headers=_headers(user2))
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()

    assert data2["tenant_id"] == empresa2.id
    assert data2["total_items_evaluados"] == 1
    item2 = data2["items"][0]
    assert item2["stock_id"] == stock2.id
    assert item2["stock_actual"] == 0
    assert item2["criticidad"] == "CRITICO"
    assert item2["reposicion_sugerida"] >= 10

    # Verificar que Tenant 2 jamás ve a stock1 de Tenant 1
    stock_ids_t2 = [it["stock_id"] for it in data2["items"]]
    assert stock1.id not in stock_ids_t2


def test_alertas_stock_predictivo_exportaciones(client: TestClient, db_session):
    """
    REQ-068: Valida la exportación de alertas predictivas a Excel y PDF.
    """
    db = db_session
    suffix = uuid4().hex[:6]
    empresa, sucursal, user = _setup_tenant(db, suffix)
    _seed_product_and_stock(db, empresa.id, sucursal.id, suffix, quantity=1)

    headers = _headers(user)

    # Exportación a Excel
    excel_resp = client.get("/api/v1/reportes/alertas-stock-predictivo/excel", headers=headers)
    assert excel_resp.status_code == 200
    assert "spreadsheetml" in excel_resp.headers.get("content-type", "")
    assert len(excel_resp.content) > 100

    # Exportación a PDF
    pdf_resp = client.get("/api/v1/reportes/alertas-stock-predictivo/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert "pdf" in pdf_resp.headers.get("content-type", "")
    assert len(pdf_resp.content) > 100
