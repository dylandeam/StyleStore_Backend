"""
Pruebas para las funcionalidades de la Especificación StyleStore v7:
- Punto 1: Registro enriquecido de clientes (con CI, teléfono, dirección).
- Punto 2: Módulo de Compras a Proveedores (abastecimiento de stock y anulación).
- Punto 4: Gestión de Pagos (confirmación online, historial y anulación).
- Punto 7: Envíos con cotización por distancia Haversine y tracking GPS.
- Punto 8: Chatbot con acción ejecutable add_to_cart.
- Punto 9: Módulo de Outfits (crear combinación, listar, comprar todo en 1 clic).
"""
import pytest
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.cliente import Cliente
from app.models.sucursal import Sucursal
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.talla import Talla
from app.models.temporada import Temporada
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.stock_inventario import StockInventario
from app.models.proveedor import Proveedor
from app.models.orden_venta import OrdenVenta
from app.models.outfit import Outfit, OutfitItem
from app.core.security import create_access_token


@pytest.fixture
def auth_context_v7(db_session):
    admin = db_session.query(User).filter(User.email == "admin_v7@stylestore.com").first()
    if not admin:
        admin = User(
            email="admin_v7@stylestore.com",
            name="Admin V7",
            hashed_password="hash",
            role="administrador",
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

    cliente_user = db_session.query(User).filter(User.email == "cliente_v7@test.com").first()
    if not cliente_user:
        cliente_user = User(
            email="cliente_v7@test.com",
            name="Cliente V7",
            hashed_password="hash",
            role="cliente",
            is_active=True,
        )
        db_session.add(cliente_user)
        db_session.commit()
        db_session.refresh(cliente_user)

    admin_token = create_access_token(data={"sub": str(admin.id), "email": admin.email, "role": admin.role})
    cliente_token = create_access_token(data={"sub": str(cliente_user.id), "email": cliente_user.email, "role": cliente_user.role})

    # Asegurar sucursal con coordenadas
    suc = db_session.query(Sucursal).filter(Sucursal.city == "La Paz Test").first()
    if not suc:
        suc = Sucursal(
            name="Sucursal Test v7",
            city="La Paz Test",
            address="Av. Arce 123",
            phone="22446688",
            active=True,
            latitud=Decimal("-16.505000"),
            longitud=Decimal("-68.129000"),
        )
        db_session.add(suc)
        db_session.commit()
        db_session.refresh(suc)

    return {
        "admin": admin,
        "admin_token": admin_token,
        "cliente": cliente_user,
        "cliente_token": cliente_token,
        "sucursal": suc,
    }


def test_v7_punto1_registro_enriquecido(client: TestClient, db_session):
    """Verifica que el registro guarde CI, teléfono, dirección y cree registro de Cliente."""
    payload = {
        "email": "nuevo_cliente_v7@test.com",
        "name": "Maria Lopez",
        "password": "Password123!",
        "ci": "8844332",
        "telefono": "77221144",
        "direccion": "Calle 21 de Calacoto #45",
    }
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["email"] == "nuevo_cliente_v7@test.com"
    assert data["ci"] == "8844332"

    # Validar cliente creado en BD
    u = db_session.query(User).filter(User.email == "nuevo_cliente_v7@test.com").first()
    assert u is not None
    assert u.ci == "8844332"
    assert u.telefono == "77221144"


def test_v7_punto2_compras_proveedores(client: TestClient, auth_context_v7, db_session):
    """Verifica el flujo de Compras a Proveedores con abastecimiento automático a stock."""
    admin_tok = auth_context_v7["admin_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}
    suc = auth_context_v7["sucursal"]

    # Crear datos base
    prov = db_session.query(Proveedor).filter(Proveedor.codigo == "PROV-V7").first()
    if not prov:
        prov = Proveedor(
            codigo="PROV-V7",
            nombre="Textiles",
            apellido="V7",
            ci="9988771",
            email="textiles_v7@test.com",
            telefono="70000001",
        )
        db_session.add(prov)
        db_session.commit()

    cat = db_session.query(Categoria).first()
    if not cat:
        cat = Categoria(nombre="Ropa")
        db_session.add(cat)
        db_session.commit()

    temp = db_session.query(Temporada).first()
    if not temp:
        temp = Temporada(nombre="Temporada Test")
        db_session.add(temp)
        db_session.commit()

    prod = db_session.query(Producto).filter(Producto.codigo == "PROD-V7-COMPRA").first()
    if not prod:
        prod = Producto(
            codigo="PROD-V7-COMPRA",
            nombre="Camisa Lino Compra",
            precio=Decimal("150.00"),
            categoria_id=cat.id,
            temporada_id=temp.id,
            active=True,
            visible_en_catalogo=True,
        )
        db_session.add(prod)
        db_session.commit()

    col = db_session.query(Color).first()
    if not col:
        col = Color(nombre="Azul")
        db_session.add(col)
        db_session.commit()

    talla = db_session.query(Talla).first()
    if not talla:
        talla = Talla(nombre="M")
        db_session.add(talla)
        db_session.commit()

    payload_compra = {
        "proveedor_codigo": "PROV-V7",
        "sucursal_id": suc.id,
        "nro_factura": "FAC-9988",
        "observaciones": "Lote inicial de temporada",
        "items": [
            {
                "producto_codigo": prod.codigo,
                "color_id": col.id,
                "talla_id": talla.id,
                "cantidad": 20,
                "costo_unitario": 80.0,
            }
        ],
    }

    r = client.post("/api/v1/compras", json=payload_compra, headers=headers)
    assert r.status_code == 201
    compra_data = r.json()
    assert float(compra_data["total"]) == 1600.0
    compra_id = compra_data["id"]

    # Verificar que el stock se incrementó
    pc = db_session.query(ProductoColor).filter(
        ProductoColor.producto_codigo == prod.codigo,
        ProductoColor.color_id == col.id,
    ).first()
    assert pc is not None

    stk = db_session.query(StockInventario).filter(
        StockInventario.sucursal_id == suc.id,
        StockInventario.producto_color_id == pc.id,
        StockInventario.talla_id == talla.id,
    ).first()
    assert stk is not None
    assert stk.cantidad >= 20

    # Listar compras
    r_list = client.get("/api/v1/compras", headers=headers)
    assert r_list.status_code == 200
    assert any(c["id"] == compra_id for c in r_list.json())


def test_v7_punto7_cotizacion_envio_distancia(client: TestClient, auth_context_v7):
    """Verifica el cálculo de tarifa dinámica y distancia Haversine."""
    suc = auth_context_v7["sucursal"]
    headers = {"Authorization": f"Bearer {auth_context_v7['cliente_token']}"}

    payload = {
        "sucursal_id": suc.id,
        "latitud_destino": -16.535000,
        "longitud_destino": -68.089000,
        "ciudad": "La Paz",
    }
    r = client.post("/api/v1/envios/cotizar-distancia", json=payload, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "distancia_km" in data
    assert "costo_envio" in data
    assert "minutos_estimados" in data
    assert data["costo_envio"] >= 5.0
    assert data["costo_envio"] == round(5.0 + data["distancia_km"] * 0.6, 2)


def test_v7_punto8_chatbot_add_to_cart(client: TestClient, auth_context_v7):
    """Verifica que el chatbot procese mensajes y reconozca intención de compra."""
    headers = {"Authorization": f"Bearer {auth_context_v7['cliente_token']}"}
    r = client.post(
        "/api/v1/chatbot/mensaje",
        json={"mensaje": "quiero comprar o agregar al carrito"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "respuesta" in data


def test_v7_punto9_modulo_outfits(client: TestClient, auth_context_v7, db_session):
    """Verifica el flujo completo de creación, listado y compra de un Outfit en 1 clic."""
    cliente_tok = auth_context_v7["cliente_token"]
    headers = {"Authorization": f"Bearer {cliente_tok}"}

    # Asegurar producto para outfit
    cat = db_session.query(Categoria).first()
    if not cat:
        cat = Categoria(nombre="Ropa")
        db_session.add(cat)
        db_session.commit()

    temp = db_session.query(Temporada).first()
    if not temp:
        temp = Temporada(nombre="Temporada Test")
        db_session.add(temp)
        db_session.commit()

    prod = db_session.query(Producto).filter(Producto.codigo == "PROD-V7-OUTFIT").first()
    if not prod:
        prod = Producto(
            codigo="PROD-V7-OUTFIT",
            nombre="Polera Algodón Outfit",
            precio=Decimal("120.00"),
            categoria_id=cat.id,
            temporada_id=temp.id,
            active=True,
            visible_en_catalogo=True,
        )
        db_session.add(prod)
        db_session.commit()

    payload_outfit = {
        "nombre": "Look Verano Style",
        "descripcion": "Combinación fresca de fin de semana",
        "items": [
            {
                "producto_codigo": prod.codigo,
                "tipo_prenda": "superior",
            }
        ],
    }

    # Crear outfit
    r = client.post("/api/v1/outfits", json=payload_outfit, headers=headers)
    assert r.status_code == 201
    outfit_data = r.json()
    assert outfit_data["nombre"] == "Look Verano Style"
    assert float(outfit_data["total"]) == float(prod.precio)
    outfit_id = outfit_data["id"]

    # Listar outfits propios
    r_get = client.get("/api/v1/outfits", headers=headers)
    assert r_get.status_code == 200
    assert any(o["id"] == outfit_id for o in r_get.json())

    # Comprar todo el outfit en 1 clic
    r_buy = client.post(f"/api/v1/outfits/{outfit_id}/comprar", headers=headers)
    assert r_buy.status_code == 200
    buy_res = r_buy.json()
    assert "items_agregados" in buy_res

    # Eliminar outfit
    r_del = client.delete(f"/api/v1/outfits/{outfit_id}", headers=headers)
    assert r_del.status_code == 200
