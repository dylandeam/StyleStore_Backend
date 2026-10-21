"""Tenant boundary regression tests for the SaaS foundation."""
from datetime import date, timedelta
from decimal import Decimal

from app.models.user import User
from app.models.cliente import Cliente
from app.models.orden_venta import OrdenVenta
from app.models.envio import Envio
from app.models.empresa import Empresa
from app.models.plan_suscripcion import ContratacionPlan
from app.models.user_empresa import UserEmpresa
from app.core.security import hash_password
from app.services.report_ai_service import ReportAIService
from app.services.plan_service import PlanService


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


def test_platform_admin_manages_tenant_lifecycle_admin_and_subscription(
    client, db_session, admin_token
):
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()
    headers = {"Authorization": f"Bearer {admin_token}"}

    created = _create_empresa(client, admin_token, "managed", "admin@managed.example.com")
    tenant_id = created["id"]
    summary = client.get("/api/v1/empresas/resumen", headers=headers)
    assert summary.status_code == 200, summary.text
    tenant = next(item for item in summary.json() if item["id"] == tenant_id)
    assert tenant["admin"]["email"] == "admin@managed.example.com"
    assert tenant["suscripcion"]["plan_codigo"] == "basico"
    assert tenant["usuarios_count"] == 1

    updated = client.patch(
        f"/api/v1/empresas/{tenant_id}",
        headers=headers,
        json={"nombre": "Managed Boutique"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["nombre"] == "Managed Boutique"

    admin_update = client.put(
        f"/api/v1/empresas/{tenant_id}/administrador",
        headers=headers,
        json={
            "name": "Nueva Administradora",
            "email": "owner@managed.example.com",
            "password": "NewTenantPass2026!",
        },
    )
    assert admin_update.status_code == 200, admin_update.text
    assert admin_update.json()["email"] == "owner@managed.example.com"

    subscription = client.put(
        f"/api/v1/empresas/{tenant_id}/suscripcion",
        headers=headers,
        json={
            "plan_codigo": "profesional",
            "fecha_inicio": "2026-10-20",
            "fecha_fin": "2027-10-20",
        },
    )
    assert subscription.status_code == 403, subscription.text
    assert "PayPal" in subscription.json()["detail"]

    tenant_login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@managed.example.com", "password": "NewTenantPass2026!"},
    )
    assert tenant_login.status_code == 200, tenant_login.text
    tenant_headers = {"Authorization": f"Bearer {tenant_login.json()['access_token']}"}

    suspended = client.put(
        f"/api/v1/empresas/{tenant_id}/estado",
        headers=headers,
        json={"active": False},
    )
    assert suspended.status_code == 200, suspended.text
    assert suspended.json()["active"] is False
    assert client.get("/api/v1/users/me", headers=tenant_headers).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "owner@managed.example.com", "password": "NewTenantPass2026!"},
    ).status_code == 401

    forbidden = client.put(
        f"/api/v1/empresas/{tenant_id}/estado",
        headers=tenant_headers,
        json={"active": True},
    )
    assert forbidden.status_code == 401

    reactivated = client.put(
        f"/api/v1/empresas/{tenant_id}/estado",
        headers=headers,
        json={"active": True},
    )
    assert reactivated.status_code == 200
    assert client.get("/api/v1/users/me", headers=tenant_headers).status_code == 200


def test_tenant_admin_cannot_access_saas_console(client, db_session, admin_token):
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()
    created = _create_empresa(client, admin_token, "private-console", "admin@private.example.com")
    tenant_headers = {"Authorization": f"Bearer {_login(client, 'admin@private.example.com')}"}

    assert client.get("/api/v1/empresas/resumen", headers=tenant_headers).status_code == 403
    assert client.get(f"/api/v1/empresas/{created['id']}", headers=tenant_headers).status_code == 403
    assert client.patch(
        f"/api/v1/empresas/{created['id']}",
        headers=tenant_headers,
        json={"nombre": "Ataque"},
    ).status_code == 403


def test_tenant_admin_cannot_see_or_modify_platform_admin_in_same_company(
    client, db_session, admin_token
):
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()

    created = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "tenant-admin@stylestore.example.com",
            "name": "Administrador Tenant",
            "password": "TenantAdmin2026!",
            "role": "administrador",
        },
    )
    assert created.status_code == 201, created.text

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "tenant-admin@stylestore.example.com",
            "password": "TenantAdmin2026!",
        },
    )
    assert login.status_code == 200, login.text
    tenant_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    visible_users = client.get("/api/v1/users", headers=tenant_headers)
    assert visible_users.status_code == 200
    assert platform_admin.email not in {item["email"] for item in visible_users.json()}

    forbidden_update = client.put(
        f"/api/v1/users/{platform_admin.id}",
        headers=tenant_headers,
        json={"is_active": False},
    )
    assert forbidden_update.status_code == 403
    db_session.refresh(platform_admin)
    assert platform_admin.is_active is True
    assert platform_admin.is_platform_admin is True

    visible_employees = client.get("/api/v1/empleados", headers=tenant_headers)
    assert visible_employees.status_code == 200
    assert platform_admin.email not in {item["email"] for item in visible_employees.json()}

    global_users = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert global_users.status_code == 200
    assert platform_admin.email in {item["email"] for item in global_users.json()}


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


def test_employee_has_workday_and_multiple_tenant_branch_schedules(
    client, db_session, admin_token
):
    platform_admin = db_session.query(User).filter(
        User.email == "admin_test@stylestore.com"
    ).one()
    platform_admin.is_platform_admin = True
    db_session.commit()
    _create_empresa(client, admin_token, "staff-schedule-a", "admin@staff-a.example.com")
    _create_empresa(client, admin_token, "staff-schedule-b", "admin@staff-b.example.com")
    headers_a = {
        "Authorization": f"Bearer {_login(client, 'admin@staff-a.example.com')}"
    }
    headers_b = {
        "Authorization": f"Bearer {_login(client, 'admin@staff-b.example.com')}"
    }

    branches_a = []
    for name in ("Centro", "Norte"):
        response = client.post(
            "/api/v1/sucursales",
            headers=headers_a,
            json={
                "name": f"Staff A {name}",
                "city": "La Paz",
                "address": f"Calle {name}",
                "phone": "70000111",
            },
        )
        assert response.status_code == 201, response.text
        branches_a.append(response.json())
    foreign_branch = client.post(
        "/api/v1/sucursales",
        headers=headers_b,
        json={
            "name": "Staff B Centro",
            "city": "Tarija",
            "address": "Calle B",
            "phone": "70000222",
        },
    ).json()

    created = client.post(
        "/api/v1/empleados",
        headers=headers_a,
        json={
            "nombre": "Lucia",
            "apellido": "Flores",
            "ci": "778899",
            "email": "lucia@staff-a.example.com",
            "password": "StaffPass2026!",
            "role": "encargado_sucursal",
            "sucursal_id": branches_a[0]["id"],
            "jornada_tipo": "medio_tiempo",
            "asignaciones": [
                {
                    "sucursal_id": branches_a[0]["id"],
                    "hora_inicio": "08:00:00",
                    "hora_fin": "12:00:00",
                    "dias_semana": ["lunes", "miercoles", "viernes"],
                },
                {
                    "sucursal_id": branches_a[1]["id"],
                    "hora_inicio": "14:00:00",
                    "hora_fin": "18:00:00",
                    "dias_semana": ["martes", "jueves"],
                },
            ],
            "edad": 27,
            "sueldo": 2800,
            "telefono": "70000333",
            "direccion": "Zona Central",
        },
    )
    assert created.status_code == 201, created.text
    employee = created.json()
    assert employee["jornada_tipo"] == "medio_tiempo"
    assert employee["sucursal_id"] == branches_a[0]["id"]
    assert {item["sucursal_id"] for item in employee["asignaciones"]} == {
        branches_a[0]["id"],
        branches_a[1]["id"],
    }
    assert employee["asignaciones"][0]["dias_semana"] == [
        "lunes", "miercoles", "viernes"
    ]

    cross_tenant = client.put(
        f"/api/v1/empleados/{employee['codigo']}",
        headers=headers_a,
        json={
            "asignaciones": [
                {
                    "sucursal_id": foreign_branch["id"],
                    "hora_inicio": "09:00:00",
                    "hora_fin": "13:00:00",
                    "dias_semana": ["lunes"],
                }
            ]
        },
    )
    assert cross_tenant.status_code == 404

    invalid_hours = client.put(
        f"/api/v1/empleados/{employee['codigo']}",
        headers=headers_a,
        json={
            "asignaciones": [
                {
                    "sucursal_id": branches_a[0]["id"],
                    "hora_inicio": "18:00:00",
                    "hora_fin": "09:00:00",
                    "dias_semana": ["lunes"],
                }
            ]
        },
    )
    assert invalid_hours.status_code == 422


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

    admin_a = db_session.query(User).filter(
        User.email == "admin-a@ops.example.com"
    ).one()
    ai_context_a = ReportAIService(
        db_session, admin_a
    )._recopilar_contexto_operativo()
    assert [item["nombre"] for item in ai_context_a["sucursales"]] == [
        "Operaciones A"
    ]
    assert ai_context_a["ventas_hoy"]["cantidad_ordenes"] == 0
    assert ai_context_a["delivery"]["total_hoy"] == 0
    assert ai_context_a["recaudacion_mes_total"] == 0


def test_three_plans_are_configurable_without_cross_tenant_changes(client, db_session, admin_token):
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()
    empresa_a = _create_empresa(client, admin_token, "plans-a", "admin-a@plans.example.com")
    empresa_b = _create_empresa(client, admin_token, "plans-b", "admin-b@plans.example.com")
    headers_a = {"Authorization": f"Bearer {_login(client, 'admin-a@plans.example.com')}"}
    headers_b = {"Authorization": f"Bearer {_login(client, 'admin-b@plans.example.com')}"}

    plans_a = client.get("/api/v1/planes", headers=headers_a)
    plans_b = client.get("/api/v1/planes", headers=headers_b)
    assert plans_a.status_code == plans_b.status_code == 200
    assert [plan["codigo"] for plan in plans_a.json()] == ["basico", "intermedio", "profesional"]
    assert [plan["codigo"] for plan in plans_b.json()] == ["basico", "intermedio", "profesional"]

    updated = client.put(
        f"/api/v1/planes/admin/intermedio?empresa_id={empresa_a['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "nombre": "Plan Boutique A", "precio_mensual": 249.90, "moneda": "USD",
            "beneficios": ["Atención prioritaria", "Panel intermedio"],
            "capacidades": {"productos": True, "ia_generativa": True},
            "estilo": {"color_primario": "#7C3AED", "destacado": True},
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["nombre"] == "Plan Boutique A"
    assert updated.json()["moneda"] == "USD"

    tenant_b_custom = next(
        plan for plan in client.get("/api/v1/planes", headers=headers_b).json()
        if plan["codigo"] == "intermedio"
    )
    assert tenant_b_custom["nombre"] == "Intermedio"
    assert tenant_b_custom["precio_mensual"] == "0.00"

    cross_update = client.put(
        f"/api/v1/planes/admin/basico?empresa_id={empresa_b['id']}",
        headers=headers_a, json={"precio_mensual": 999},
    )
    assert cross_update.status_code == 403

    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "client-a@plans.example.com", "password": "ClientPass2026!",
            "name": "Cliente Plan A", "empresa_codigo": "plans-a",
        },
    )
    assert register.status_code == 201, register.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "client-a@plans.example.com", "password": "ClientPass2026!"},
    )
    client_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    public_plans = client.get("/api/v1/planes", headers=client_headers)
    assert next(plan for plan in public_plans.json() if plan["codigo"] == "intermedio")["nombre"] == "Plan Boutique A"

    forbidden_client_contract = client.post(
        "/api/v1/planes/contratar", headers=client_headers,
        json={"plan_codigo": "intermedio"},
    )
    assert forbidden_client_contract.status_code == 403

    paypal_order = client.post(
        "/api/v1/planes/paypal/crear-orden", headers=headers_a,
        json={"plan_codigo": "intermedio"},
    )
    assert paypal_order.status_code == 200, paypal_order.text
    contracted = client.post(
        "/api/v1/planes/paypal/capturar-orden", headers=headers_a,
        json={"paypal_order_id": paypal_order.json()["id"]},
    )
    assert contracted.status_code == 200, contracted.text
    assert contracted.json()["plan_nombre"] == "Plan Boutique A"
    assert contracted.json()["precio"] == "249.90"
    assert client.get("/api/v1/planes/mi-contratacion", headers=client_headers).json()["estado"] == "activa"

    master_updates_b = client.put(
        f"/api/v1/planes/admin/basico?empresa_id={empresa_b['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"precio_mensual": 79, "moneda": "BOB"},
    )
    assert master_updates_b.status_code == 200
    assert master_updates_b.json()["empresa_id"] == empresa_b["id"]
    assert empresa_a["id"] != empresa_b["id"]


def test_basic_plan_blocks_third_active_branch(client, db_session, admin_token):
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()
    _create_empresa(client, admin_token, "branch-limit", "admin@branch-limit.example.com")
    headers = {"Authorization": f"Bearer {_login(client, 'admin@branch-limit.example.com')}"}

    for number in (1, 2):
        response = client.post(
            "/api/v1/sucursales",
            headers=headers,
            json={
                "name": f"Sucursal {number}",
                "city": "La Paz",
                "address": f"Calle {number}",
                "phone": f"7000000{number}",
            },
        )
        assert response.status_code == 201, response.text

    blocked = client.post(
        "/api/v1/sucursales",
        headers=headers,
        json={"name": "Sucursal 3", "city": "La Paz", "address": "Calle 3", "phone": "70000003"},
    )
    assert blocked.status_code == 403
    assert "permite hasta 2 sucursales" in blocked.json()["detail"]


def test_plan_minimums_and_operational_capabilities_are_enforced(
    client, db_session, admin_token
):
    company = _create_empresa(
        client, admin_token, "capabilities", "admin@capabilities.example.com"
    )
    tenant_headers = {
        "Authorization": f"Bearer {_login(client, 'admin@capabilities.example.com')}"
    }
    master_headers = {"Authorization": f"Bearer {admin_token}"}

    basic = client.put(
        f"/api/v1/planes/admin/basico?empresa_id={company['id']}",
        headers=master_headers,
        json={
            "capacidades": {
                "productos": False,
                "ventas": False,
                "reservas": False,
                "offline": False,
                "reportes": False,
                "chatbot": True,
                "predicciones": True,
                "ia_generativa": True,
            }
        },
    )
    assert basic.status_code == 200, basic.text
    assert all(
        basic.json()["capacidades"][capability] is True
        for capability in ("productos", "ventas", "reservas", "offline", "reportes")
    )
    assert basic.json()["ia_generativa"] is False
    assert basic.json()["capacidades"]["ia_generativa"] is False
    assert basic.json()["capacidades"]["chatbot"] is False
    assert basic.json()["capacidades"]["predicciones"] is False

    blocked_chatbot = client.post(
        "/api/v1/chatbot/mensaje",
        headers=tenant_headers,
        json={"mensaje": "Hola"},
    )
    assert blocked_chatbot.status_code == 403
    assert "chatbot" in blocked_chatbot.json()["detail"]

    assigned = client.put(
        f"/api/v1/empresas/{company['id']}/suscripcion",
        headers=master_headers,
        json={"plan_codigo": "intermedio"},
    )
    assert assigned.status_code == 403, assigned.text
    tenant_admin = db_session.query(User).filter(User.email == "admin@capabilities.example.com").one()
    assigned_contract = PlanService(db_session).contract(tenant_admin, "intermedio")
    assert assigned_contract.plan.codigo == "intermedio"
    assert assigned_contract.plan.max_sucursales == 5

    intermediate = client.put(
        f"/api/v1/planes/admin/intermedio?empresa_id={company['id']}",
        headers=master_headers,
        json={"capacidades": {"chatbot": False, "predicciones": True}},
    )
    assert intermediate.status_code == 200, intermediate.text
    assert intermediate.json()["max_sucursales"] == 5
    assert intermediate.json()["capacidades"]["chatbot"] is True
    assert intermediate.json()["capacidades"]["predicciones"] is False

    allowed_chatbot = client.post(
        "/api/v1/chatbot/mensaje",
        headers=tenant_headers,
        json={"mensaje": "Hola"},
    )
    assert allowed_chatbot.status_code == 200, allowed_chatbot.text
    allowed_report = client.get(
        "/api/v1/reportes/dashboard-stats", headers=tenant_headers
    )
    assert allowed_report.status_code == 200, allowed_report.text

    contract = db_session.query(ContratacionPlan).filter(
        ContratacionPlan.empresa_id == company["id"],
        ContratacionPlan.estado == "activa",
    ).order_by(ContratacionPlan.id.desc()).first()
    contract.fecha_fin = date.today() - timedelta(days=1)
    db_session.commit()
    expired = client.get("/api/v1/reportes/dashboard-stats", headers=tenant_headers)
    assert expired.status_code == 403
    assert "inactivo hasta renovar" in expired.json()["detail"]

    db_session.refresh(contract)
    company_row = db_session.query(Empresa).filter(Empresa.id == company["id"]).one()
    db_session.refresh(company_row)
    assert contract.estado == "vencida"
    assert company_row.active is False
    assert company_row.inactive_reason == "subscription_expired"

    # The expired tenant administrator keeps only the renewal surface available.
    plans = client.get("/api/v1/planes", headers=tenant_headers)
    assert plans.status_code == 200, plans.text
    unpaid = client.post(
        "/api/v1/planes/contratar",
        headers=tenant_headers,
        json={"plan_codigo": "intermedio", "pago_confirmado": False},
    )
    assert unpaid.status_code == 400
    assert "confirmar el pago" in unpaid.json()["detail"]

    priced = client.put(
        f"/api/v1/planes/admin/intermedio?empresa_id={company['id']}", headers=master_headers,
        json={"precio_mensual": 49.90, "moneda": "USD"},
    )
    assert priced.status_code == 200, priced.text
    renewal_order = client.post(
        "/api/v1/planes/paypal/crear-orden", headers=tenant_headers,
        json={"plan_codigo": "intermedio"},
    )
    assert renewal_order.status_code == 200, renewal_order.text
    renewed = client.post(
        "/api/v1/planes/paypal/capturar-orden", headers=tenant_headers,
        json={"paypal_order_id": renewal_order.json()["id"]},
    )
    assert renewed.status_code == 200, renewed.text
    assert renewed.json()["estado_pago"] == "pagado"
    assert renewed.json()["referencia_pago"].startswith("CAP-PAYPAL-")

    db_session.refresh(company_row)
    assert company_row.active is True
    assert company_row.inactive_reason is None
    restored_report = client.get(
        "/api/v1/reportes/dashboard-stats", headers=tenant_headers
    )
    assert restored_report.status_code == 200, restored_report.text


def test_client_can_register_in_multiple_tenants(client, db_session, admin_token):
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()
    company_a = _create_empresa(client, admin_token, "multi-a", "admin-a@multi.example.com")
    company_b = _create_empresa(client, admin_token, "multi-b", "admin-b@multi.example.com")

    public = client.get("/api/v1/empresas/publicas/registro")
    assert public.status_code == 200
    assert {"multi-a", "multi-b"}.issubset({item["codigo"] for item in public.json()})

    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "multi-client@example.com",
            "password": "ClientPass2026!",
            "name": "Cliente Multi",
            "empresa_codigos": ["multi-a", "multi-b"],
        },
    )
    assert registered.status_code == 201, registered.text
    user = db_session.query(User).filter(User.email == "multi-client@example.com").one()
    memberships = db_session.query(UserEmpresa).filter(UserEmpresa.user_id == user.id).all()
    assert {item.empresa_id for item in memberships} == {company_a["id"], company_b["id"]}

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "multi-client@example.com", "password": "ClientPass2026!"},
    )
    client_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    tenants = client.get("/api/v1/auth/tenants", headers=client_headers)
    assert tenants.status_code == 200, tenants.text
    assert {item["id"] for item in tenants.json()} == {company_a["id"], company_b["id"]}
    switched = client.post(
        "/api/v1/auth/tenants/select", headers=client_headers,
        json={"empresa_id": company_b["id"]},
    )
    assert switched.status_code == 200, switched.text
    switched_headers = {"Authorization": f"Bearer {switched.json()['access_token']}"}
    assert client.get("/api/v1/users/me", headers=switched_headers).json()["empresa_id"] == company_b["id"]

    admin_headers = []
    for email in ("admin-a@multi.example.com", "admin-b@multi.example.com"):
        headers = {"Authorization": f"Bearer {_login(client, email)}"}
        admin_headers.append(headers)
        listed = client.get("/api/v1/clientes", headers=headers)
        assert listed.status_code == 200, listed.text
        assert any(item["email"] == "multi-client@example.com" for item in listed.json())

    removed = client.delete(
        f"/api/v1/clientes/{db_session.query(Cliente).filter(Cliente.user_id == user.id).one().codigo}",
        headers=admin_headers[0],
    )
    assert removed.status_code == 200, removed.text
    assert not any(
        item["email"] == "multi-client@example.com"
        for item in client.get("/api/v1/clientes", headers=admin_headers[0]).json()
    )
    assert any(
        item["email"] == "multi-client@example.com"
        for item in client.get("/api/v1/clientes", headers=admin_headers[1]).json()
    )
    db_session.refresh(user)
    assert user.is_active is True
