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


@pytest.fixture
def admin_token(db_session, client):
    """Fixture providing an authenticated administrator token."""
    # Ensure admin user exists in test DB
    admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").first()
    if not admin:
        admin = User(
            email="admin_test@stylestore.com",
            name="Admin Test",
            hashed_password=hash_password("AdminPass123!"),
            role="administrador",
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()

    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_test@stylestore.com", "password": "AdminPass123!"},
    )
    return res.json()["access_token"]


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
    """Test full CRUD cycle for products catalog."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create
    create_res = client.post(
        "/api/v1/productos",
        headers=headers,
        json={
            "name": "Chaqueta Cuero Premium",
            "description": "Chaqueta de cuero genuino estilo urbano",
            "category": "Chaquetas",
            "size": "L",
            "color": "Negro",
            "price": "149.99",
            "stock": 25,
            "active": True,
        },
    )
    assert create_res.status_code == 201
    prod_id = create_res.json()["id"]

    # List
    list_res = client.get("/api/v1/productos", headers=headers)
    assert list_res.status_code == 200
    assert any(p["id"] == prod_id for p in list_res.json())

    # Update
    update_res = client.put(
        f"/api/v1/productos/{prod_id}",
        headers=headers,
        json={"stock": 30, "price": "139.99"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["stock"] == 30
    assert update_res.json()["price"] == "139.99"

    # Delete
    del_res = client.delete(f"/api/v1/productos/{prod_id}", headers=headers)
    assert del_res.status_code == 200


def test_cliente_can_view_productos_and_sucursales(client):
    """Verify that a client role can view products and branches, but cannot create them."""
    # Register client user
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "cliente_test@stylestore.com",
            "password": "Password123!",
            "name": "Cliente Test",
        },
    )
    assert reg_res.status_code == 201

    # Login as client
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "cliente_test@stylestore.com", "password": "Password123!"},
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
            "name": "Intento no autorizado",
            "category": "Ropa",
            "size": "M",
            "color": "Azul",
            "price": "99.99",
            "stock": 10,
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

