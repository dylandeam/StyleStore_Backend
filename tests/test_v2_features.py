"""
Comprehensive tests for StyleStore v2 features:
- CU1: Employee registration by Admin with assigned roles
- CU4: Password change with email token confirmation
- CU5: Roles & RBAC permissions management
- CU6: Bitacora audit logs
- Sucursales CRUD
- Productos CRUD
"""
import pytest
from app.models.user import User
from app.core.security import hash_password




def test_admin_create_employee(client, admin_token):
    """CU1: Admin can create an employee with specific role."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "cajero1@stylestore.com",
            "name": "Carlos Cajero",
            "password": "CajeroPass123!",
            "role": "cajero",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "cajero1@stylestore.com"
    assert data["role"] == "cajero"


def test_roles_and_permissions(client, admin_token):
    """CU5: List roles, list permissions, and update role permissions."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. List roles
    res = client.get("/api/v1/roles", headers=headers)
    assert res.status_code == 200
    roles = res.json()
    assert len(roles) >= 4

    # 2. Get permissions for cajero
    res_perm = client.get("/api/v1/roles/cajero/permissions", headers=headers)
    assert res_perm.status_code == 200
    assert "permissions" in res_perm.json()

    # 3. Update permissions for cajero
    res_update = client.put(
        "/api/v1/roles/cajero/permissions",
        headers=headers,
        json={"permission_codes": ["productos.ver", "sucursales.ver"]},
    )
    assert res_update.status_code == 200
    updated_perms = [p["code"] for p in res_update.json()["permissions"]]
    assert "productos.ver" in updated_perms
    assert "sucursales.ver" in updated_perms


def test_password_change_flow(client, db_session):
    """CU4: Request password change, extract token, and confirm."""
    # 1. Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "pass_test@stylestore.com",
            "name": "Password User",
            "password": "OldPassword123!",
        },
    )

    # 2. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "pass_test@stylestore.com", "password": "OldPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Request password change
    req_res = client.post(
        "/api/v1/password/request-change",
        headers=headers,
        json={
            "current_password": "OldPassword123!",
            "new_password": "NewPassword123!",
            "new_password_confirmation": "NewPassword123!",
        },
    )
    assert req_res.status_code == 200
    assert "enviado" in req_res.json()["message"].lower()

    # 4. Fetch the token generated in database
    from app.models.password_reset_token import PasswordResetToken
    token_record = (
        db_session.query(PasswordResetToken)
        .order_by(PasswordResetToken.id.desc())
        .first()
    )
    assert token_record is not None

    # 5. Confirm password change
    confirm_res = client.post(
        "/api/v1/password/confirm",
        json={"token": token_record.token},
    )
    assert confirm_res.status_code == 200

    # 6. Verify login with NEW password works
    new_login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "pass_test@stylestore.com", "password": "NewPassword123!"},
    )
    assert new_login_res.status_code == 200
    assert "access_token" in new_login_res.json()


def test_bitacora_logs(client, admin_token):
    """CU6: View audit log entries."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/bitacora", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) > 0


def test_sucursales_crud(client, admin_token):
    """Test full CRUD cycle for store branches."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create
    create_res = client.post(
        "/api/v1/sucursales",
        headers=headers,
        json={
            "name": "Sucursal Central",
            "city": "Santa Cruz",
            "address": "Av. Monseñor Rivero #450",
            "phone": "+591-3-3344556",
            "active": True,
        },
    )
    assert create_res.status_code == 201
    sucursal_id = create_res.json()["id"]

    # List
    list_res = client.get("/api/v1/sucursales", headers=headers)
    assert list_res.status_code == 200
    assert any(s["id"] == sucursal_id for s in list_res.json())

    # Update
    update_res = client.put(
        f"/api/v1/sucursales/{sucursal_id}",
        headers=headers,
        json={"phone": "+591-3-9988776"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["phone"] == "+591-3-9988776"

    # Delete
    del_res = client.delete(f"/api/v1/sucursales/{sucursal_id}", headers=headers)
    assert del_res.status_code == 200


def test_productos_crud(client, admin_token):
    """Test full CRUD cycle for products catalog conforming to v4 diagram."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Ensure a category and season exist
    cat_res = client.post(
        "/api/v1/categorias",
        headers=headers,
        json={"nombre": "Chaquetas Test"},
    )
    if cat_res.status_code == 201:
        cat_id = cat_res.json()["id"]
    else:
        cats = client.get("/api/v1/categorias", headers=headers).json()
        cat_id = cats[0]["id"]

    temp_res = client.post(
        "/api/v1/temporadas",
        headers=headers,
        json={"nombre": "Invierno 2026 Test"},
    )
    if temp_res.status_code == 201:
        temp_id = temp_res.json()["id"]
    else:
        temps = client.get("/api/v1/temporadas", headers=headers).json()
        temp_id = temps[0]["id"]

    # Create product
    create_res = client.post(
        "/api/v1/productos",
        headers=headers,
        json={
            "nombre": "Chaqueta Cuero Premium",
            "descripcion": "Chaqueta de cuero genuino estilo urbano",
            "categoria_id": cat_id,
            "temporada_id": temp_id,
            "precio": "149.99",
            "active": True,
        },
    )
    assert create_res.status_code == 201
    prod_codigo = create_res.json()["codigo"]

    # List
    list_res = client.get("/api/v1/productos", headers=headers)
    assert list_res.status_code == 200
    assert any(p["codigo"] == prod_codigo for p in list_res.json())

    # Update
    update_res = client.put(
        f"/api/v1/productos/{prod_codigo}",
        headers=headers,
        json={"precio": "139.99", "nombre": "Chaqueta Cuero Modificada"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["precio"] == "139.99"
    assert update_res.json()["nombre"] == "Chaqueta Cuero Modificada"

    # Delete
    del_res = client.delete(f"/api/v1/productos/{prod_codigo}", headers=headers)
    assert del_res.status_code == 200


def test_cliente_can_view_productos_and_sucursales(client):
    """Verify that a client role can view products and branches, but cannot create them."""
    # Register client user
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "cliente_test_v4@stylestore.com",
            "password": "Password123!",
            "name": "Cliente Test",
        },
    )
    assert reg_res.status_code in [201, 400]

    # Login as client
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "cliente_test_v4@stylestore.com", "password": "Password123!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Can list productos
    prod_res = client.get("/api/v1/productos", headers=headers)
    assert prod_res.status_code == 200

    # Can list sucursales
    suc_res = client.get("/api/v1/sucursales", headers=headers)
    assert suc_res.status_code == 200

    # Cannot create producto (403 Forbidden)
    create_prod_res = client.post(
        "/api/v1/productos",
        headers=headers,
        json={
            "nombre": "Intento no autorizado",
            "categoria_id": 1,
            "temporada_id": 1,
            "precio": "99.99",
        },
    )
    assert create_prod_res.status_code == 403

    # Cannot create sucursal (403 Forbidden)
    create_suc_res = client.post(
        "/api/v1/sucursales",
        headers=headers,
        json={
            "name": "Sucursal no autorizada",
            "address": "Calle 1",
            "city": "Santa Cruz",
        },
    )
    assert create_suc_res.status_code == 403

