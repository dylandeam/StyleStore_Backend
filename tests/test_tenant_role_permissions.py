from uuid import uuid4

from app.core.security import create_access_token, hash_password
from app.models.empresa import Empresa
from app.models.role import Role
from app.models.user import User
from app.services.role_service import RoleService


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "empresa_id": user.empresa_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _tenant(db, suffix: str) -> tuple[Empresa, User, User, Role]:
    empresa = Empresa(codigo=f"rbac-{suffix}", nombre=f"RBAC {suffix}", active=True)
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    service = RoleService(db, empresa.id)
    service.seed_default_permissions_and_roles()
    admin_role = db.query(Role).filter(Role.empresa_id == empresa.id, Role.nombre == "Administrador").one()
    client_role = db.query(Role).filter(Role.empresa_id == empresa.id, Role.nombre == "Cliente").one()
    admin = User(
        empresa_id=empresa.id,
        email=f"admin-{suffix}-{uuid4().hex[:6]}@test.local",
        name="Admin",
        hashed_password=hash_password("Pass123!"),
        role="administrador",
        role_id=admin_role.id,
        is_active=True,
    )
    client = User(
        empresa_id=empresa.id,
        email=f"client-{suffix}-{uuid4().hex[:6]}@test.local",
        name="Cliente",
        hashed_password=hash_password("Pass123!"),
        role="cliente",
        role_id=client_role.id,
        is_active=True,
    )
    db.add_all([admin, client])
    db.commit()
    return empresa, admin, client, client_role


def test_permissions_are_tenant_scoped_persistent_and_enforced(client, db_session, admin_token):
    empresa_a, admin_a, client_a, client_role_a = _tenant(db_session, "a")
    empresa_b, _, client_b, client_role_b = _tenant(db_session, "b")
    master_a = {
        "Authorization": f"Bearer {admin_token}",
        "X-Tenant-Context": str(empresa_a.id),
    }

    current = client.get(f"/api/v1/roles/{client_role_a.id}/permissions", headers=master_a)
    assert current.status_code == 200, current.text
    codes = [item["code"] for item in current.json()["permissions"]]
    assert "resenas.crear" in codes

    updated = client.put(
        f"/api/v1/roles/{client_role_a.id}/permissions",
        headers=master_a,
        json={"permission_codes": [code for code in codes if code != "resenas.crear"]},
    )
    assert updated.status_code == 200, updated.text

    # Reloading/seed reconciliation must not silently restore a disabled permission.
    RoleService(db_session, empresa_a.id).seed_default_permissions_and_roles()
    mine_a = client.get("/api/v1/roles/me/permissions", headers=_headers(client_a))
    mine_b = client.get("/api/v1/roles/me/permissions", headers=_headers(client_b))
    assert "resenas.crear" not in mine_a.json()["permission_codes"]
    assert "resenas.crear" in mine_b.json()["permission_codes"]

    blocked = client.put(
        "/api/v1/productos/NO-EXISTE/resenas/mia",
        headers=_headers(client_a),
        json={"puntuacion": 5, "comentario": "Quiero comprar esta prenda."},
    )
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "Las reseñas no están disponibles temporalmente en esta tienda."

    # The same capability remains active in the other tenant (the product lookup
    # can fail, but it must not be rejected as a disabled feature).
    unaffected = client.put(
        "/api/v1/productos/NO-EXISTE/resenas/mia",
        headers=_headers(client_b),
        json={"puntuacion": 5, "comentario": "Quiero comprar esta prenda."},
    )
    assert unaffected.status_code != 403

    # A tenant administrator cannot mutate a role that belongs to another tenant.
    cross_tenant = client.put(
        f"/api/v1/roles/{client_role_b.id}/permissions",
        headers=_headers(admin_a),
        json={"permission_codes": []},
    )
    assert cross_tenant.status_code == 404
