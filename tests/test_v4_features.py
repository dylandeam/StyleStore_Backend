"""
Tests para funcionalidades oficiales de la Especificación v4 (Diagrama DB).
Pruebas de CRUD para Categorías, Colores, Tallas, Temporadas, Empleados, Clientes, Proveedores y Stock.
"""
import pytest


def test_catalogo_maestros_crud(client, admin_token):
    """Test CRUD de Categorías, Colores, Tallas y Temporadas."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Categoria
    cat_res = client.post("/api/v1/categorias", headers=headers, json={"nombre": "Calzados Deportivos"})
    assert cat_res.status_code == 201
    cat_id = cat_res.json()["id"]

    # 2. Color
    col_res = client.post("/api/v1/colores", headers=headers, json={"nombre": "Rojo Escarlata"})
    assert col_res.status_code == 201
    col_id = col_res.json()["id"]

    # 3. Talla
    tal_res = client.post("/api/v1/tallas", headers=headers, json={"nombre": "42 EU"})
    assert tal_res.status_code == 201
    tal_id = tal_res.json()["id"]

    # 4. Temporada
    tem_res = client.post("/api/v1/temporadas", headers=headers, json={"nombre": "Verano 2026"})
    assert tem_res.status_code == 201
    tem_id = tem_res.json()["id"]

    # Validar listados
    assert any(c["id"] == cat_id for c in client.get("/api/v1/categorias", headers=headers).json())
    assert any(c["id"] == col_id for c in client.get("/api/v1/colores", headers=headers).json())
    assert any(t["id"] == tal_id for t in client.get("/api/v1/tallas", headers=headers).json())
    assert any(t["id"] == tem_id for t in client.get("/api/v1/temporadas", headers=headers).json())


def test_proveedor_crud(client, admin_token):
    """Test CRUD de Proveedores con autogeneración de Código PROV-XXXX."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    create_res = client.post(
        "/api/v1/proveedores",
        headers=headers,
        json={
            "nombre": "Textiles del Valle",
            "apellido": "Guzman",
            "email": "contacto@textilesdelvalle.com",
            "telefono": "77123456",
        },
    )
    assert create_res.status_code == 201
    data = create_res.json()
    assert data["codigo"].startswith("PROV-")
    prov_cod = data["codigo"]

    # Get by codigo
    get_res = client.get(f"/api/v1/proveedores/{prov_cod}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["nombre"] == "Textiles del Valle"

    # Update
    upd_res = client.put(
        f"/api/v1/proveedores/{prov_cod}",
        headers=headers,
        json={"telefono": "77999999"},
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["telefono"] == "77999999"

    # Delete
    del_res = client.delete(f"/api/v1/proveedores/{prov_cod}", headers=headers)
    assert del_res.status_code == 200


def test_empleado_generacion_codigo(client, admin_token):
    """Test de creación de Empleado con algoritmo de código: letra_ap + letra_nom + ci[:4]."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    import uuid

    unique_name = f"Sucursal Emp {uuid.uuid4().hex[:6]}"
    suc_res = client.post(
        "/api/v1/sucursales",
        headers=headers,
        json={"name": unique_name, "address": "Av. Principal 123", "city": "Cochabamba", "phone": "+591-4-4567890"},
    )
    assert suc_res.status_code == 201
    sucursal_id = suc_res.json()["id"]

    # Crear empleado
    emp_res = client.post(
        "/api/v1/empleados",
        headers=headers,
        json={
            "nombre": "Carlos",
            "apellido": "Mamani",
            "ci": "8473920",
            "email": f"carlos_{uuid.uuid4().hex[:6]}@stylestore.com",
            "password": "Password123!",
            "sucursal_id": sucursal_id,
            "edad": 28,
            "sueldo": "3500.00",
            "telefono": "78901234",
            "direccion": "Av. Heroinas 456",
        },
    )
    assert emp_res.status_code == 201
    emp_data = emp_res.json()
    # Código debe ser 'M' (apellido Mamani) + 'C' (nombre Carlos) + '8473' (primeros 4 dígitos de ci)
    assert emp_data["codigo"] == "MC8473"
    assert emp_data["edad"] == 28
    assert emp_data["sueldo"] == "3500.00"

    # Listar empleados
    list_res = client.get("/api/v1/empleados", headers=headers)
    assert list_res.status_code == 200
    assert any(e["codigo"] == "MC8473" for e in list_res.json())
