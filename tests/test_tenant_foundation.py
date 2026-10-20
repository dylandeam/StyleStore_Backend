"""Tenant boundary regression tests for the SaaS foundation."""
from decimal import Decimal

from app.models.user import User
from app.models.cliente import Cliente
from app.models.orden_venta import OrdenVenta
from app.models.envio import Envio
from app.core.security import hash_password


def _create_empresa(client, admin_token: str, codigo: str, email: str) -> dict:
    response = client.post(
        "/api/v1/empresas",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "codigo": codigo,
            "nombre": f"Empresa {codigo.upper()}",
            "admin_email": email,
            "admin_name": f"Admin {codigo.upper()}",
            "admin_password": "TenantPass2026!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _login(client, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TenantPass2026!"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_platform_admin_creates_isolated_tenants_and_branches(client, db_session, admin_token):
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()

    empresa_a = _create_empresa(client, admin_token, "tenant-a", "admin-a@tenant.example.com")
    empresa_b = _create_empresa(client, admin_token, "tenant-b", "admin-b@tenant.example.com")
    token_a = _login(client, "admin-a@tenant.example.com")
    token_b = _login(client, "admin-b@tenant.example.com")

    branch_a = client.post(
        "/api/v1/sucursales",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Sucursal Tenant A", "city": "La Paz", "address": "Calle A 123", "phone": "70000001"},
    )
    branch_b = client.post(
        "/api/v1/sucursales",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"name": "Sucursal Tenant B", "city": "Santa Cruz", "address": "Calle B 456", "phone": "70000002"},
    )
    assert branch_a.status_code == 201, branch_a.text
    assert branch_b.status_code == 201, branch_b.text
    assert branch_a.json()["empresa_id"] == empresa_a["id"]
    assert branch_b.json()["empresa_id"] == empresa_b["id"]

    list_a = client.get("/api/v1/sucursales", headers={"Authorization": f"Bearer {token_a}"})
    assert [item["name"] for item in list_a.json()] == ["Sucursal Tenant A"]

    cross_read = client.get(
        f"/api/v1/sucursales/{branch_b.json()['id']}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert cross_read.status_code == 404

    users_a = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token_a}"})
    assert users_a.status_code == 200
    assert {user["email"] for user in users_a.json()} == {"admin-a@tenant.example.com"}


def test_tenant_admin_cannot_list_or_create_companies(client, db_session, admin_token):
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()
    _create_empresa(client, admin_token, "tenant-c", "admin-c@tenant.example.com")
    tenant_token = _login(client, "admin-c@tenant.example.com")

    assert client.get("/api/v1/empresas", headers={"Authorization": f"Bearer {tenant_token}"}).status_code == 403
    response = client.post(
        "/api/v1/empresas",
        headers={"Authorization": f"Bearer {tenant_token}"},
        json={
            "codigo": "forbidden",
            "nombre": "Forbidden",
            "admin_email": "forbidden@tenant.example.com",
            "admin_name": "Forbidden Admin",
            "admin_password": "TenantPass2026!",
        },
    )
    assert response.status_code == 403


def test_legacy_registration_defaults_to_stylestore_when_other_tenants_exist(client, db_session, admin_token):
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()
    _create_empresa(client, admin_token, "tenant-d", "admin-d@tenant.example.com")

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "legacy-client@example.com",
            "password": "ClientPass2026!",
            "name": "Cliente Legado",
        },
    )
    assert response.status_code == 201, response.text
    stylestore_id = response.json()["empresa_id"]
    assert stylestore_id is not None
    assert stylestore_id != client.get(
        "/api/v1/empresas/mia",
        headers={"Authorization": f"Bearer {_login(client, 'admin-d@tenant.example.com')}"},
    ).json()["id"]


def test_staff_clients_and_inventory_are_hidden_between_tenants(client, db_session, admin_token):
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()

    _create_empresa(client, admin_token, "scope-a", "admin-a@scope.example.com")
    _create_empresa(client, admin_token, "scope-b", "admin-b@scope.example.com")
    token_a = _login(client, "admin-a@scope.example.com")
    token_b = _login(client, "admin-b@scope.example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    branch_a = client.post(
        "/api/v1/sucursales",
        headers=headers_a,
        json={
            "name": "Scope A Central", "city": "La Paz", "address": "Avenida A 100",
            "phone": "70000011", "hora_apertura": "10:00:00", "hora_cierre": "16:00:00",
        },
    )
    branch_b = client.post(
        "/api/v1/sucursales",
        headers=headers_b,
        json={"name": "Scope B Central", "city": "Tarija", "address": "Avenida B 200", "phone": "70000012"},
    )
    assert branch_a.status_code == 201
    assert branch_a.json()["hora_apertura"] == "10:00:00"
    assert branch_b.status_code == 201

    employee_b = client.post(
        "/api/v1/empleados", headers=headers_b,
        json={
            "nombre": "Empleado", "apellido": "Tenant B", "ci": "880011",
            "email": "staff-b@scope.example.com", "password": "StaffPass2026!", "role": "cajero",
            "sucursal_id": branch_b.json()["id"], "edad": 25, "sueldo": 3000,
            "telefono": "70000013", "direccion": "Dirección B",
        },
    )
    assert employee_b.status_code == 201, employee_b.text
    employee_code = employee_b.json()["codigo"]
    employees_a = client.get("/api/v1/empleados", headers=headers_a).json()
    assert all(item["email"] != "staff-b@scope.example.com" for item in employees_a)
    assert client.get(f"/api/v1/empleados/{employee_code}", headers=headers_a).status_code == 404

    foreign_branch_employee = client.post(
        "/api/v1/empleados", headers=headers_a,
        json={
            "nombre": "Cruce", "apellido": "Bloqueado", "ci": "880012",
            "email": "cross@scope.example.com", "password": "StaffPass2026!", "role": "cajero",
            "sucursal_id": branch_b.json()["id"], "edad": 26, "sueldo": 3000,
            "telefono": "70000014", "direccion": "Dirección A",
        },
    )
    assert foreign_branch_employee.status_code == 404

    client_b = client.post(
        "/api/v1/clientes", headers=headers_b,
        json={
            "nombre": "Cliente", "apellido": "Tenant B", "ci": "990011",
            "email": "client-b@scope.example.com", "password": "ClientPass2026!",
            "telefono": "70000015", "direccion": "Dirección cliente B",
        },
    )
    assert client_b.status_code == 201, client_b.text
    assert client.get("/api/v1/clientes", headers=headers_a).json() == []
    assert client.get(f"/api/v1/clientes/{client_b.json()['codigo']}", headers=headers_a).status_code == 404
    assert client.get(
        f"/api/v1/inventario/sucursal/{branch_b.json()['id']}", headers=headers_a
    ).status_code == 404


def test_catalog_roots_are_isolated_and_names_can_repeat_per_tenant(client, db_session, admin_token):
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()
    _create_empresa(client, admin_token, "catalog-a", "admin-a@catalog.example.com")
    _create_empresa(client, admin_token, "catalog-b", "admin-b@catalog.example.com")
    headers_a = {"Authorization": f"Bearer {_login(client, 'admin-a@catalog.example.com')}"}
    headers_b = {"Authorization": f"Bearer {_login(client, 'admin-b@catalog.example.com')}"}

    category_a = client.post("/api/v1/categorias", headers=headers_a, json={"nombre": "Casual"})
    category_b = client.post("/api/v1/categorias", headers=headers_b, json={"nombre": "Casual"})
    assert category_a.status_code == 201, category_a.text
    assert category_b.status_code == 201, category_b.text
    assert category_a.json()["id"] != category_b.json()["id"]
    assert client.get(f"/api/v1/categorias/{category_b.json()['id']}", headers=headers_a).status_code == 404
    assert [item["id"] for item in client.get("/api/v1/categorias", headers=headers_a).json()] == [category_a.json()["id"]]

    season_a = client.post("/api/v1/temporadas", headers=headers_a, json={"nombre": "Verano"})
    season_b = client.post("/api/v1/temporadas", headers=headers_b, json={"nombre": "Verano"})
    color_b = client.post("/api/v1/colores", headers=headers_b, json={"nombre": "Azul"})
    size_b = client.post("/api/v1/tallas", headers=headers_b, json={"nombre": "M"})
    assert season_a.status_code == season_b.status_code == 201
    assert color_b.status_code == size_b.status_code == 201

    product_b = client.post(
        "/api/v1/productos", headers=headers_b,
        json={
            "codigo": "CAT-B-001", "nombre": "Prenda privada B", "precio": 120,
            "categoria_id": category_b.json()["id"], "temporada_id": season_b.json()["id"],
            "color_ids": [color_b.json()["id"]],
        },
    )
    assert product_b.status_code == 201, product_b.text
    assert client.get("/api/v1/productos/CAT-B-001", headers=headers_a).status_code == 404
    assert all(item["codigo"] != "CAT-B-001" for item in client.get("/api/v1/productos", headers=headers_a).json())

    cross_reference = client.post(
        "/api/v1/productos", headers=headers_a,
        json={
            "codigo": "CAT-A-X", "nombre": "Cruce inválido", "precio": 90,
            "categoria_id": category_b.json()["id"], "temporada_id": season_a.json()["id"],
        },
    )
    assert cross_reference.status_code == 404

    supplier_b = client.post(
        "/api/v1/proveedores", headers=headers_b,
        json={
            "codigo": "SUP-B-001", "nombre": "Proveedor", "apellido": "Privado",
            "email": "supplier-b@catalog.example.com", "telefono": "70000100",
            "categoria_ids": [category_b.json()["id"]],
        },
    )
    assert supplier_b.status_code == 201, supplier_b.text
    assert client.get("/api/v1/proveedores/SUP-B-001", headers=headers_a).status_code == 404


def test_orders_payments_shipments_and_reports_are_isolated(client, db_session, admin_token):
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()
    empresa_a = _create_empresa(client, admin_token, "ops-a", "admin-a@ops.example.com")
    empresa_b = _create_empresa(client, admin_token, "ops-b", "admin-b@ops.example.com")
    headers_a = {"Authorization": f"Bearer {_login(client, 'admin-a@ops.example.com')}"}
    headers_b = {"Authorization": f"Bearer {_login(client, 'admin-b@ops.example.com')}"}

    branch_a = client.post(
        "/api/v1/sucursales", headers=headers_a,
        json={"name": "Operaciones A", "city": "La Paz", "address": "Calle A", "phone": "70000201"},
    ).json()
    branch_b = client.post(
        "/api/v1/sucursales", headers=headers_b,
        json={"name": "Operaciones B", "city": "Tarija", "address": "Calle B", "phone": "70000202"},
    ).json()
    assert branch_a["empresa_id"] == empresa_a["id"]
    assert branch_b["empresa_id"] == empresa_b["id"]

    buyer_b = User(
        empresa_id=empresa_b["id"], email="buyer-b@ops.example.com", name="Buyer B",
        hashed_password=hash_password("ClientPass2026!"), role="cliente", is_active=True,
    )
    db_session.add(buyer_b)
    db_session.flush()
    profile_b = Cliente(
        codigo="CLI-OPS-B", user_id=buyer_b.id, telefono="70000203", direccion="Dirección B"
    )
    db_session.add(profile_b)
    db_session.flush()
    order_b = OrdenVenta(
        codigo_cliente=profile_b.codigo, sucursal_id=branch_b["id"], total=Decimal("155.00"),
        estado="pendiente", tipo_venta="en_linea",
    )
    db_session.add(order_b)
    db_session.flush()
    shipment_b = Envio(
        orden_venta_id=order_b.id, direccion="Destino B", ciudad="Tarija",
        costo=Decimal("10.00"), estado="pendiente",
    )
    db_session.add(shipment_b)
    db_session.commit()

    assert client.get(f"/api/v1/ventas/{order_b.id}", headers=headers_a).status_code == 404
    assert client.post(
        "/api/v1/pagos/caja",
        headers=headers_a,
        json={"orden_venta_id": order_b.id, "efectivo_recibido": 200},
    ).status_code == 404
    assert client.patch(
        f"/api/v1/envios/{shipment_b.id}/delivery",
        headers=headers_a,
        json={"estado": "en camino"},
    ).status_code == 404

    report_a = client.get("/api/v1/reportes/ventas/preview", headers=headers_a)
    assert report_a.status_code == 200
    assert all(item["id"] != order_b.id for item in report_a.json()["items"])
    dashboard_a = client.get("/api/v1/reportes/dashboard-stats", headers=headers_a)
    assert dashboard_a.status_code == 200
    assert dashboard_a.json()["total_ventas"] == 0
