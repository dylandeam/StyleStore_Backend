"""
Pruebas automatizadas para REQ-058:
Gestión integral de reservas por tenant/sucursal, búsqueda multicriterio,
estados y expiración automática con restitución atómica de existencias.
"""
from datetime import date, timedelta, time
from decimal import Decimal
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.models.empresa import Empresa
from app.models.sucursal import Sucursal
from app.models.user import User
from app.models.cliente import Cliente
from app.models.categoria import Categoria
from app.models.temporada import Temporada
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.color import Color
from app.models.talla import Talla
from app.models.stock_inventario import StockInventario
from app.models.reserva import Reserva, DetalleReserva
from app.services.plan_service import PlanService


def _headers(user: User) -> dict:
    tok = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
    return {"Authorization": f"Bearer {tok}"}


def _seed_item(db, empresa_id: int, sucursal_id: int, nombre_prod: str, codigo_prod: str, quantity: int = 5) -> StockInventario:
    suffix = uuid4().hex[:6]
    cat = Categoria(empresa_id=empresa_id, nombre=f"Cat {suffix}")
    temp = Temporada(empresa_id=empresa_id, nombre=f"Temp {suffix}")
    col = Color(empresa_id=empresa_id, nombre=f"Col {suffix}")
    sz = Talla(empresa_id=empresa_id, nombre=f"T-{suffix}")
    db.add_all([cat, temp, col, sz])
    db.flush()

    prod = Producto(
        empresa_id=empresa_id,
        codigo=codigo_prod,
        nombre=nombre_prod,
        precio=Decimal("350.00"),
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
    return stock


def test_reservas_expiracion_automatica_y_restitucion_stock(client: TestClient, db_session):
    """
    REQ-058: Reserva con fecha pasada debe ser marcada como 'vencida' y devolver
    el stock reservado al inventario correspondiente.
    """
    db = db_session
    suffix = uuid4().hex[:6]

    empresa = Empresa(nombre=f"Tenant Res {suffix}", codigo=f"res-{suffix}", active=True)
    db.add(empresa)
    db.commit()

    sucursal = Sucursal(
        empresa_id=empresa.id,
        name=f"Sucursal Central {suffix}",
        city="Santa Cruz",
        address="Av. Banzer Km 4",
        phone="77711223",
        active=True,
        hora_apertura=time(8, 0),
        hora_cierre=time(20, 0),
    )
    db.add(sucursal)
    db.commit()

    admin_user = User(
        email=f"admin_{suffix}@test.com",
        name="Admin",
        apellido="Res",
        role="administrador",
        empresa_id=empresa.id,
        is_active=True,
        hashed_password=hash_password("Pass123!"),
    )
    cliente_user = User(
        email=f"cliente_{suffix}@test.com",
        name="Carlos",
        apellido="Montes",
        role="cliente",
        empresa_id=empresa.id,
        is_active=True,
        hashed_password=hash_password("Pass123!"),
    )
    db.add_all([admin_user, cliente_user])
    db.commit()

    # Contratar plan para habilitar tenant
    PlanService(db).contract(admin_user, "profesional")

    cliente = Cliente(
        codigo=f"CL-CARLOS-{suffix}",
        user_id=cliente_user.id,
        telefono="78901234",
        direccion="Calle Los Pinos 10",
    )
    db.add(cliente)
    db.commit()

    stock = _seed_item(
        db,
        empresa_id=empresa.id,
        sucursal_id=sucursal.id,
        nombre_prod="Chaqueta Cuero Exclusiva",
        codigo_prod=f"PROD-EXP-{suffix}",
        quantity=10,
    )

    # Simular reserva vencida de 3 unidades creada en el pasado (ayer)
    fecha_ayer = date.today() - timedelta(days=1)
    reserva = Reserva(
        fecha=fecha_ayer,
        hora=time(10, 0),
        estado="pendiente",
        codigo_cliente=cliente.codigo,
        sucursal_id=sucursal.id,
        tipo="reserva_prenda",
    )
    db.add(reserva)
    db.flush()

    stock.cantidad -= 3  # Stock queda en 7
    det = DetalleReserva(
        reserva_id=reserva.id,
        stock_inventario_id=stock.id,
        cantidad=3,
    )
    db.add(det)
    db.commit()

    assert stock.cantidad == 7
    assert reserva.estado == "pendiente"

    # Invocar endpoint POST /api/v1/reservas/expirar-vencidas
    admin_hdr = _headers(admin_user)
    resp = client.post(
        f"/api/v1/reservas/expirar-vencidas?sucursal_id={sucursal.id}",
        headers=admin_hdr,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["procesadas"] >= 1
    assert data["stock_restituido"] >= 3

    # Verificar que en BD la reserva ahora tiene estado 'vencida' y el stock volvió a 10
    db.refresh(reserva)
    db.refresh(stock)
    assert reserva.estado == "vencida"
    assert stock.cantidad == 10


def test_reservas_busqueda_multicriterio_y_aislamiento_tenant(client: TestClient, db_session):
    """
    REQ-058: Búsqueda flexible por texto (search) y aislamiento estricto por tenant.
    """
    db = db_session
    suffix1 = uuid4().hex[:6]
    suffix2 = uuid4().hex[:6]

    # Tenant 1
    emp1 = Empresa(nombre=f"Tenant Alfa {suffix1}", codigo=f"alfa-{suffix1}", active=True)
    db.add(emp1)
    db.commit()

    suc1 = Sucursal(
        empresa_id=emp1.id,
        name=f"Sucursal Alfa Centro {suffix1}",
        city="Cochabamba",
        address="Av. Heroínas 100",
        phone="71122334",
        active=True,
    )
    db.add(suc1)
    db.commit()

    admin1 = User(
        email=f"admin_alfa_{suffix1}@test.com",
        name="AdminAlfa",
        role="administrador",
        empresa_id=emp1.id,
        is_active=True,
        hashed_password=hash_password("Pass123!"),
    )
    cli_user1 = User(
        email=f"valeria_{suffix1}@test.com",
        name="Valeria",
        apellido="Suarez",
        role="cliente",
        empresa_id=emp1.id,
        is_active=True,
        hashed_password=hash_password("Pass123!"),
    )
    db.add_all([admin1, cli_user1])
    db.commit()

    PlanService(db).contract(admin1, "profesional")

    cli1 = Cliente(
        codigo=f"CL-VALERIA-{suffix1}",
        user_id=cli_user1.id,
        telefono="79988776",
        direccion="Calle Bolívar 50",
    )
    db.add(cli1)
    db.commit()

    stk1 = _seed_item(
        db,
        empresa_id=emp1.id,
        sucursal_id=suc1.id,
        nombre_prod="Vestido Gala Esmeralda",
        codigo_prod=f"VEST-ESM-{suffix1}",
        quantity=5,
    )

    fecha_hoy = date.today()
    res1 = Reserva(
        fecha=fecha_hoy,
        hora=time(15, 0),
        estado="pendiente",
        codigo_cliente=cli1.codigo,
        sucursal_id=suc1.id,
        tipo="reserva_prenda",
    )
    db.add(res1)
    db.flush()
    det1 = DetalleReserva(
        reserva_id=res1.id,
        stock_inventario_id=stk1.id,
        cantidad=1,
    )
    db.add(det1)
    db.commit()

    # Tenant 2 (aislado)
    emp2 = Empresa(nombre=f"Tenant Beta {suffix2}", codigo=f"beta-{suffix2}", active=True)
    db.add(emp2)
    db.commit()

    suc2 = Sucursal(
        empresa_id=emp2.id,
        name=f"Sucursal Beta Norte {suffix2}",
        city="La Paz",
        address="Av. Ballivián 20",
        phone="72233445",
        active=True,
    )
    db.add(suc2)
    db.commit()

    admin2 = User(
        email=f"admin_beta_{suffix2}@test.com",
        name="AdminBeta",
        role="administrador",
        empresa_id=emp2.id,
        is_active=True,
        hashed_password=hash_password("Pass123!"),
    )
    db.add(admin2)
    db.commit()

    PlanService(db).contract(admin2, "profesional")

    hdr1 = _headers(admin1)
    hdr2 = _headers(admin2)

    # 1. Búsqueda por texto (nombre de cliente 'Valeria') en Tenant 1
    resp_busqueda_cli = client.get("/api/v1/reservas?search=Valeria", headers=hdr1)
    assert resp_busqueda_cli.status_code == 200
    items_cli = resp_busqueda_cli.json()
    assert len(items_cli) == 1
    assert items_cli[0]["codigo_cliente"] == cli1.codigo

    # 2. Búsqueda por nombre de prenda ('Esmeralda') en Tenant 1
    resp_busqueda_prod = client.get("/api/v1/reservas?search=Esmeralda", headers=hdr1)
    assert resp_busqueda_prod.status_code == 200
    items_prod = resp_busqueda_prod.json()
    assert len(items_prod) == 1
    assert items_prod[0]["detalles"][0]["producto_codigo"] == f"VEST-ESM-{suffix1}"

    # 3. Aislamiento tenant: Tenant 2 buscando 'Valeria' o 'Esmeralda' debe obtener 0 resultados
    resp_t2 = client.get("/api/v1/reservas?search=Valeria", headers=hdr2)
    assert resp_t2.status_code == 200
    assert len(resp_t2.json()) == 0

    resp_t2_all = client.get("/api/v1/reservas", headers=hdr2)
    assert resp_t2_all.status_code == 200
    assert len(resp_t2_all.json()) == 0
