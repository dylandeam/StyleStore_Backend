"""
Tests para funcionalidades añadidas en Especificación StyleStore v5.
"""
from decimal import Decimal
import pytest


def test_v5_dynamic_roles_crud(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Crear nuevo rol dinámico
    create_res = client.post(
        "/api/v1/roles",
        headers=headers,
        json={"nombre": "Auditor Financiero", "descripcion": "Revisa reportes y ventas"},
    )
    assert create_res.status_code == 201
    role_id = create_res.json()["id"]

    # 2. Listar roles y verificar inclusión
    list_res = client.get("/api/v1/roles", headers=headers)
    assert list_res.status_code == 200
    roles = list_res.json()
    assert any(r["id"] == role_id for r in roles)

    # 3. Asignar permisos al rol
    assign_res = client.put(
        f"/api/v1/roles/{role_id}/permissions",
        headers=headers,
        json={"permission_codes": ["ventas.ver", "bitacora.ver"]},
    )
    assert assign_res.status_code == 200
    perms = [p["code"] for p in assign_res.json()["permissions"]]
    assert "ventas.ver" in perms

    # 4. Actualizar rol
    update_res = client.put(
        f"/api/v1/roles/{role_id}",
        headers=headers,
        json={"descripcion": "Descripción actualizada"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["descripcion"] == "Descripción actualizada"

    # 5. Eliminar rol (sin usuarios asociados)
    del_res = client.delete(f"/api/v1/roles/{role_id}", headers=headers)
    assert del_res.status_code == 200


def test_v5_colecciones_crud(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Crear colección
    res = client.post(
        "/api/v1/colecciones",
        headers=headers,
        json={"nombre": "Colección Vintage 2026", "descripcion": "Moda clásica y elegante"},
    )
    assert res.status_code == 201
    col_id = res.json()["id"]

    # 2. Listar colecciones
    list_res = client.get("/api/v1/colecciones", headers=headers)
    assert list_res.status_code == 200
    assert any(c["id"] == col_id for c in list_res.json())

    # 3. Eliminar colección
    del_res = client.delete(f"/api/v1/colecciones/{col_id}", headers=headers)
    assert del_res.status_code == 200


def test_v5_proveedor_with_ci(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    res = client.post(
        "/api/v1/proveedores",
        headers=headers,
        json={
            "ci": "87654321",
            "nombre": "Roberto",
            "apellido": "Gomez",
            "email": "roberto.gomez@proveedorv5.com",
            "telefono": "78945612",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["codigo"].startswith("PR-")
    assert "87654321"[-4:] in data["codigo"]
    assert data["ci"] == "87654321"

    # Cleanup
    client.delete(f"/api/v1/proveedores/{data['codigo']}", headers=headers)


def test_v5_profile_edit(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Actualizar datos personales
    patch_res = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={
            "name": "Administrador Modificado",
            "telefono": "76543210",
            "direccion": "Av. Central 123",
        },
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["name"] == "Administrador Modificado"
    assert data["telefono"] == "76543210"
    assert data["direccion"] == "Av. Central 123"


def test_v5_envio_cotizacion(client):
    res = client.post("/api/v1/envios/cotizar", json={"distancia_km": 2.5})
    assert res.status_code == 200
    assert float(res.json()["costo"]) == 6.5

    res2 = client.post("/api/v1/envios/cotizar", json={"distancia_km": 7.0})
    assert res2.status_code == 200
    assert float(res2.json()["costo"]) == 9.2
