"""Tenant boundary regression tests for the SaaS foundation."""
from app.models.user import User


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
