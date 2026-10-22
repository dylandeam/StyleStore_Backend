"""
Tests reproducibles de reportes multi-tenant y comparativa de sucursales (REQ-039, REQ-040, REQ-063).
Verifica:
1. Aislamiento estricto de todas las familias de reportes entre empresas independientes.
2. Comparativa agregada de sucursales del tenant autenticado con métricas y exportables.
3. Rechazo HTTP 404 inmediato al intentar filtrar reportes con el ID de sucursal de otra empresa.
"""
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.sucursal import Sucursal
from app.models.user import User
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.color import Color
from app.models.talla import Talla
from app.models.categoria import Categoria
from app.models.temporada import Temporada
from app.models.stock_inventario import StockInventario
from app.models.orden_venta import OrdenVenta, DetalleVenta
from app.services.plan_service import PlanService
from app.core.security import hash_password, create_access_token


def _setup_multiempresa_data(db_session: Session):
    """Crea dos tenants aislados con sucursales, productos, stock y ventas."""
    # Tenant 1: Alpha
    emp_alpha = db_session.query(Empresa).filter(Empresa.codigo == "rep_alpha").first()
    if not emp_alpha:
        emp_alpha = Empresa(
            codigo="rep_alpha",
            nombre="Empresa Alpha Fashion",
            active=True,
        )
        db_session.add(emp_alpha)
        db_session.commit()

    # Tenant 2: Beta
    emp_beta = db_session.query(Empresa).filter(Empresa.codigo == "rep_beta").first()
    if not emp_beta:
        emp_beta = Empresa(
            codigo="rep_beta",
            nombre="Empresa Beta Outfits",
            active=True,
        )
        db_session.add(emp_beta)
        db_session.commit()

    # Sucursales de Alpha (2 sucursales)
    suc_a1 = db_session.query(Sucursal).filter(Sucursal.empresa_id == emp_alpha.id, Sucursal.name == "Alpha Central").first()
    if not suc_a1:
        suc_a1 = Sucursal(
            empresa_id=emp_alpha.id,
            name="Alpha Central",
            city="La Paz",
            address="Av. Montes 100",
            phone="71000001",
            active=True,
        )
        db_session.add(suc_a1)

    suc_a2 = db_session.query(Sucursal).filter(Sucursal.empresa_id == emp_alpha.id, Sucursal.name == "Alpha Norte").first()
    if not suc_a2:
        suc_a2 = Sucursal(
            empresa_id=emp_alpha.id,
            name="Alpha Norte",
            city="Cochabamba",
            address="Av. Heroinas 200",
            phone="71000002",
            active=True,
        )
        db_session.add(suc_a2)

    # Sucursal de Beta (1 sucursal)
    suc_b1 = db_session.query(Sucursal).filter(Sucursal.empresa_id == emp_beta.id, Sucursal.name == "Beta Express").first()
    if not suc_b1:
        suc_b1 = Sucursal(
            empresa_id=emp_beta.id,
            name="Beta Express",
            city="Santa Cruz",
            address="Calle 21 de Mayo 300",
            phone="72000001",
            active=True,
        )
        db_session.add(suc_b1)
    db_session.commit()

    # Usuarios Admin para Alpha y Beta
    u_alpha = db_session.query(User).filter(User.email == "admin_alpha@rep.com").first()
    if not u_alpha:
        u_alpha = User(
            empresa_id=emp_alpha.id,
            email="admin_alpha@rep.com",
            name="Admin Alpha",
            hashed_password=hash_password("Pass123!"),
            role="administrador",
            is_active=True,
        )
        db_session.add(u_alpha)

    u_beta = db_session.query(User).filter(User.email == "admin_beta@rep.com").first()
    if not u_beta:
        u_beta = User(
            empresa_id=emp_beta.id,
            email="admin_beta@rep.com",
            name="Admin Beta",
            hashed_password=hash_password("Pass123!"),
            role="administrador",
            is_active=True,
        )
        db_session.add(u_beta)
    db_session.commit()

    # Suscripciones
    PlanService(db_session).contract(u_alpha, "profesional")
    PlanService(db_session).contract(u_beta, "profesional")

    # Categorías y temporadas
    cat_a = db_session.query(Categoria).filter(Categoria.empresa_id == emp_alpha.id).first()
    if not cat_a:
        cat_a = Categoria(nombre="Ropa Alpha", empresa_id=emp_alpha.id)
        db_session.add(cat_a)

    temp_a = db_session.query(Temporada).filter(Temporada.empresa_id == emp_alpha.id).first()
    if not temp_a:
        temp_a = Temporada(nombre="Verano Alpha", empresa_id=emp_alpha.id)
        db_session.add(temp_a)

    cat_b = db_session.query(Categoria).filter(Categoria.empresa_id == emp_beta.id).first()
    if not cat_b:
        cat_b = Categoria(nombre="Ropa Beta", empresa_id=emp_beta.id)
        db_session.add(cat_b)

    temp_b = db_session.query(Temporada).filter(Temporada.empresa_id == emp_beta.id).first()
    if not temp_b:
        temp_b = Temporada(nombre="Invierno Beta", empresa_id=emp_beta.id)
        db_session.add(temp_b)
    db_session.commit()

    prod_a = db_session.query(Producto).filter(Producto.empresa_id == emp_alpha.id).first()
    if not prod_a:
        prod_a = Producto(
            codigo="PROD-ALPHA-01",
            empresa_id=emp_alpha.id,
            nombre="Camisa Lino Alpha",
            descripcion="Camisa premium de lino",
            precio=Decimal("120.00"),
            categoria_id=cat_a.id,
            temporada_id=temp_a.id,
            active=True,
            visible_en_catalogo=True,
        )
        db_session.add(prod_a)

    prod_b = db_session.query(Producto).filter(Producto.empresa_id == emp_beta.id).first()
    if not prod_b:
        prod_b = Producto(
            codigo="PROD-BETA-01",
            empresa_id=emp_beta.id,
            nombre="Chaqueta Cuero Beta",
            descripcion="Chaqueta exclusiva Beta",
            precio=Decimal("9999.00"),
            categoria_id=cat_b.id,
            temporada_id=temp_b.id,
            active=True,
            visible_en_catalogo=True,
        )
        db_session.add(prod_b)
    db_session.commit()

    col = db_session.query(Color).filter(Color.empresa_id == emp_alpha.id, Color.nombre == "Azul Marino").first()
    if not col:
        col = Color(empresa_id=emp_alpha.id, nombre="Azul Marino")
        db_session.add(col)
        db_session.commit()

    talla = db_session.query(Talla).filter(Talla.empresa_id == emp_alpha.id, Talla.nombre == "M").first()
    if not talla:
        talla = Talla(empresa_id=emp_alpha.id, nombre="M")
        db_session.add(talla)
        db_session.commit()

    pc_a = db_session.query(ProductoColor).filter(ProductoColor.producto_codigo == prod_a.codigo).first()
    if not pc_a:
        pc_a = ProductoColor(producto_codigo=prod_a.codigo, color_id=col.id)
        db_session.add(pc_a)

    pc_b = db_session.query(ProductoColor).filter(ProductoColor.producto_codigo == prod_b.codigo).first()
    if not pc_b:
        pc_b = ProductoColor(producto_codigo=prod_b.codigo, color_id=col.id)
        db_session.add(pc_b)
    db_session.commit()

    st_a1 = db_session.query(StockInventario).filter(StockInventario.sucursal_id == suc_a1.id).first()
    if not st_a1:
        st_a1 = StockInventario(
            producto_color_id=pc_a.id,
            talla_id=talla.id,
            sucursal_id=suc_a1.id,
            cantidad=30,
        )
        db_session.add(st_a1)

    st_a2 = db_session.query(StockInventario).filter(StockInventario.sucursal_id == suc_a2.id).first()
    if not st_a2:
        st_a2 = StockInventario(
            producto_color_id=pc_a.id,
            talla_id=talla.id,
            sucursal_id=suc_a2.id,
            cantidad=4,
        )
        db_session.add(st_a2)

    st_b1 = db_session.query(StockInventario).filter(StockInventario.sucursal_id == suc_b1.id).first()
    if not st_b1:
        st_b1 = StockInventario(
            producto_color_id=pc_b.id,
            talla_id=talla.id,
            sucursal_id=suc_b1.id,
            cantidad=100,
        )
        db_session.add(st_b1)
    db_session.commit()

    ov_a1 = db_session.query(OrdenVenta).filter(OrdenVenta.sucursal_id == suc_a1.id).first()
    if not ov_a1:
        ov1 = OrdenVenta(
            sucursal_id=suc_a1.id,
            total=Decimal("150.00"),
            metodo_pago="efectivo",
            estado="pagada",
            tipo_venta="presencial",
        )
        ov2 = OrdenVenta(
            sucursal_id=suc_a1.id,
            total=Decimal("200.00"),
            metodo_pago="qr",
            estado="pagada",
            tipo_venta="presencial",
        )
        db_session.add_all([ov1, ov2])
        db_session.commit()

        db_session.add(DetalleVenta(
            orden_venta_id=ov1.id,
            producto_nombre=prod_a.nombre,
            cantidad=1,
            precio_unitario=Decimal("150.00"),
            subtotal=Decimal("150.00"),
        ))
        db_session.commit()

    ov_a2 = db_session.query(OrdenVenta).filter(OrdenVenta.sucursal_id == suc_a2.id).first()
    if not ov_a2:
        ov3 = OrdenVenta(
            sucursal_id=suc_a2.id,
            total=Decimal("500.00"),
            metodo_pago="paypal",
            estado="pagada",
            tipo_venta="en_linea",
        )
        db_session.add(ov3)
        db_session.commit()

        db_session.add(DetalleVenta(
            orden_venta_id=ov3.id,
            producto_nombre=prod_a.nombre,
            cantidad=2,
            precio_unitario=Decimal("250.00"),
            subtotal=Decimal("500.00"),
        ))
        db_session.commit()

    ov_b = db_session.query(OrdenVenta).filter(OrdenVenta.sucursal_id == suc_b1.id).first()
    if not ov_b:
        ov_beta = OrdenVenta(
            sucursal_id=suc_b1.id,
            total=Decimal("9999.00"),
            metodo_pago="paypal",
            estado="pagada",
            tipo_venta="en_linea",
        )
        db_session.add(ov_beta)
        db_session.commit()

        db_session.add(DetalleVenta(
            orden_venta_id=ov_beta.id,
            producto_nombre=prod_b.nombre,
            cantidad=1,
            precio_unitario=Decimal("9999.00"),
            subtotal=Decimal("9999.00"),
        ))
        db_session.commit()

    token_alpha = create_access_token(data={"sub": str(u_alpha.id), "email": u_alpha.email, "role": u_alpha.role})
    token_beta = create_access_token(data={"sub": str(u_beta.id), "email": u_beta.email, "role": u_beta.role})

    return {
        "emp_alpha": emp_alpha,
        "emp_beta": emp_beta,
        "suc_a1": suc_a1,
        "suc_a2": suc_a2,
        "suc_b1": suc_b1,
        "token_alpha": token_alpha,
        "token_beta": token_beta,
    }


def test_reporte_ventas_aislamiento_multitenant(client: TestClient, db_session: Session):
    """Verifica que el reporte de ventas aísle estrictamente las órdenes del tenant autenticado."""
    data = _setup_multiempresa_data(db_session)
    headers_alpha = {"Authorization": f"Bearer {data['token_alpha']}"}
    headers_beta = {"Authorization": f"Bearer {data['token_beta']}"}

    # 1. Preview de ventas Alpha: total debe incluir solo ventas Alpha (850.00), nunca 9999.00
    res_a = client.get("/api/v1/reportes/ventas/preview", headers=headers_alpha)
    assert res_a.status_code == 200
    body_a = res_a.json()
    assert body_a["total_registros"] >= 3
    assert float(body_a["total_monto"]) >= 850.0
    for item in body_a["items"]:
        assert float(item["total"]) != 9999.0
        assert item["sucursal_nombre"] in ["Alpha Central", "Alpha Norte"]

    # 2. Preview de ventas Beta: debe ver su venta de 9999 y ninguna de Alpha
    res_b = client.get("/api/v1/reportes/ventas/preview", headers=headers_beta)
    assert res_b.status_code == 200
    body_b = res_b.json()
    assert body_b["total_registros"] >= 1
    assert any(float(i["total"]) == 9999.0 for i in body_b["items"])
    for item in body_b["items"]:
        assert item["sucursal_nombre"] == "Beta Express"

    # 3. Exportables Excel y PDF de ventas Alpha
    res_excel = client.get("/api/v1/reportes/ventas/excel", headers=headers_alpha)
    assert res_excel.status_code == 200
    assert "application/vnd.openxmlformats" in res_excel.headers["content-type"]
    assert len(res_excel.content) > 1000

    res_pdf = client.get("/api/v1/reportes/ventas/pdf", headers=headers_alpha)
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.headers["content-type"]
    assert len(res_pdf.content) > 1000


def test_reporte_inventario_aislamiento_multitenant(client: TestClient, db_session: Session):
    """Verifica que el inventario no filtre ni exponga existencias de otro tenant."""
    data = _setup_multiempresa_data(db_session)
    headers_alpha = {"Authorization": f"Bearer {data['token_alpha']}"}

    res_a = client.get("/api/v1/reportes/inventario/preview", headers=headers_alpha)
    assert res_a.status_code == 200
    items_a = res_a.json()["items"]
    for it in items_a:
        assert "PROD-BETA" not in it["codigo"]
        assert it["sucursal_nombre"] in ["Alpha Central", "Alpha Norte"]

    # Filtro solo bajo stock
    res_criticos = client.get("/api/v1/reportes/inventario/preview?solo_bajo_stock=true", headers=headers_alpha)
    assert res_criticos.status_code == 200
    for it in res_criticos.json()["items"]:
        assert it["cantidad"] <= 5

    # Exportables
    res_xl = client.get("/api/v1/reportes/inventario/excel", headers=headers_alpha)
    assert res_xl.status_code == 200
    res_pdf = client.get("/api/v1/reportes/inventario/pdf", headers=headers_alpha)
    assert res_pdf.status_code == 200


def test_comparativa_sucursales_metricas_y_aislamiento(client: TestClient, db_session: Session):
    """
    Verifica REQ-063:
    1. Agregación y comparación side-by-side de las sucursales del tenant autenticado.
    2. Cálculo de porcentajes de participación de ventas, órdenes y stock crítico.
    3. Exclusión total de sucursales de otras empresas.
    """
    data = _setup_multiempresa_data(db_session)
    headers_alpha = {"Authorization": f"Bearer {data['token_alpha']}"}

    res = client.get("/api/v1/reportes/comparativa-sucursales/preview", headers=headers_alpha)
    assert res.status_code == 200
    comp = res.json()

    assert comp["total_sucursales"] == 2
    assert comp["gran_total_ventas"] >= 850.0
    assert comp["gran_total_ordenes"] >= 3

    nombres_sucursales = [s["nombre"] for s in comp["sucursales"]]
    assert "Alpha Central" in nombres_sucursales
    assert "Alpha Norte" in nombres_sucursales
    assert "Beta Express" not in nombres_sucursales

    suc_central = next(s for s in comp["sucursales"] if s["nombre"] == "Alpha Central")
    assert suc_central["total_ventas"] >= 350.0
    assert suc_central["cantidad_ordenes"] >= 2
    assert suc_central["ticket_promedio"] > 0
    assert suc_central["total_stock"] >= 30
    assert suc_central["desglose_pagos"]["efectivo"] >= 150.0
    assert suc_central["desglose_pagos"]["qr"] >= 200.0

    suc_norte = next(s for s in comp["sucursales"] if s["nombre"] == "Alpha Norte")
    assert suc_norte["total_ventas"] >= 500.0
    assert suc_norte["cantidad_ordenes"] >= 1
    assert suc_norte["items_criticos"] >= 1
    assert suc_norte["desglose_pagos"]["paypal"] >= 500.0

    # Exportables de comparativa
    res_xl = client.get("/api/v1/reportes/comparativa-sucursales/excel", headers=headers_alpha)
    assert res_xl.status_code == 200
    assert "application/vnd.openxmlformats" in res_xl.headers["content-type"]
    assert len(res_xl.content) > 1000

    res_pdf = client.get("/api/v1/reportes/comparativa-sucursales/pdf", headers=headers_alpha)
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.headers["content-type"]
    assert len(res_pdf.content) > 1000


def test_rechazo_filtro_sucursal_ajena_404(client: TestClient, db_session: Session):
    """
    Verifica que pasar el ID de sucursal de otro tenant en cualquier endpoint de reporte
    devuelva 404 de inmediato, sin revelar datos ajenos ni permitir sondas.
    """
    data = _setup_multiempresa_data(db_session)
    headers_alpha = {"Authorization": f"Bearer {data['token_alpha']}"}
    id_sucursal_beta = data["suc_b1"].id

    res_v = client.get(f"/api/v1/reportes/ventas/preview?sucursal_id={id_sucursal_beta}", headers=headers_alpha)
    assert res_v.status_code == 404

    res_i = client.get(f"/api/v1/reportes/inventario/preview?sucursal_id={id_sucursal_beta}", headers=headers_alpha)
    assert res_i.status_code == 404

    res_e = client.get(f"/api/v1/reportes/empleados/preview?sucursal_id={id_sucursal_beta}", headers=headers_alpha)
    assert res_e.status_code == 404

    res_f = client.get(f"/api/v1/reportes/financiero/preview?sucursal_id={id_sucursal_beta}", headers=headers_alpha)
    assert res_f.status_code == 404

    res_c = client.get(f"/api/v1/reportes/compras/preview?sucursal_id={id_sucursal_beta}", headers=headers_alpha)
    assert res_c.status_code == 404

    res_ex = client.get(f"/api/v1/reportes/ventas/excel?sucursal_id={id_sucursal_beta}", headers=headers_alpha)
    assert res_ex.status_code == 404


def test_familias_reportes_dinamicos_aisladas(client: TestClient, db_session: Session):
    """Verifica el aislamiento multi-tenant en las familias dinámicas de reportes (REQ-040)."""
    data = _setup_multiempresa_data(db_session)
    headers_alpha = {"Authorization": f"Bearer {data['token_alpha']}"}

    res_mv = client.get("/api/v1/reportes/mas-vendidos/preview", headers=headers_alpha)
    assert res_mv.status_code == 200
    prods = [p["producto"] for p in res_mv.json()["items"]]
    assert any("Alpha" in p for p in prods)
    assert not any("Beta" in p for p in prods)

    res_fin = client.get("/api/v1/reportes/financiero/preview", headers=headers_alpha)
    assert res_fin.status_code == 200
    for f in res_fin.json()["items"]:
        assert float(f["total_recaudado"]) < 9999.0
