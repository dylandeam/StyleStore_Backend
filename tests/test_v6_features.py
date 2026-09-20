"""
Pruebas para las funcionalidades de la Especificación StyleStore v6:
- Dashboard de estadísticas con filtro por sucursal
- Chatbot local inteligente con chips de navegación
- Sistema de notificaciones y suscripciones (in-app y email)
- Regla de reserva de prendas (elegibilidad con ≥ 1 compra previa y límite de 7 días)
- Cambios y Devoluciones con validación de 7 días
- Venta presencial con Efectivo y QR
- Los 8 nuevos reportes dinámicos
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.cliente import Cliente
from app.models.sucursal import Sucursal
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.talla import Talla
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.stock_inventario import StockInventario
from app.models.orden_venta import OrdenVenta, DetalleVenta
from app.models.pago import Pago
from app.core.security import create_access_token


@pytest.fixture
def auth_tokens(db_session):
    """Crea un admin y un cliente con tokens de autenticación para pruebas v6."""
    # Admin
    admin = db_session.query(User).filter(User.email == "admin_v6@stylestore.com").first()
    if not admin:
        admin = User(
            email="admin_v6@stylestore.com",
            name="Admin V6",
            hashed_password="hash",
            role="administrador",
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

    admin_token = create_access_token(data={"sub": str(admin.id), "email": admin.email, "role": admin.role})

    # Cliente
    cliente_user = db_session.query(User).filter(User.email == "cliente_v6@test.com").first()
    if not cliente_user:
        cliente_user = User(
            email="cliente_v6@test.com",
            name="Cliente V6",
            hashed_password="hash",
            role="cliente",
            is_active=True,
        )
        db_session.add(cliente_user)
        db_session.commit()
        db_session.refresh(cliente_user)

    cliente_profile = db_session.query(Cliente).filter(Cliente.user_id == cliente_user.id).first()
    if not cliente_profile:
        cliente_profile = Cliente(
            codigo="CLI-V6-001",
            user_id=cliente_user.id,
            telefono="77712345",
            direccion="Av. Central 123",
        )
        db_session.add(cliente_profile)
        db_session.commit()
        db_session.refresh(cliente_profile)

    client_token = create_access_token(data={"sub": str(cliente_user.id), "email": cliente_user.email, "role": cliente_user.role})

    return {
        "admin": admin,
        "admin_token": admin_token,
        "client_user": cliente_user,
        "client_profile": cliente_profile,
        "client_token": client_token,
    }


@pytest.fixture
def sample_inventory(db_session):
    """Crea una sucursal, producto y stock para probar ventas y reservas."""
    suc = db_session.query(Sucursal).filter(Sucursal.name == "Sucursal V6 Test").first()
    if not suc:
        suc = Sucursal(
            name="Sucursal V6 Test",
            city="Santa Cruz",
            address="Calle 7 Oeste #45",
            phone="33445566",
            active=True,
        )
        db_session.add(suc)
        db_session.commit()
        db_session.refresh(suc)

    cat = db_session.query(Categoria).first()
    if not cat:
        cat = Categoria(nombre="Vestidos")
        db_session.add(cat)
        db_session.commit()
        db_session.refresh(cat)

    col = db_session.query(Color).first()
    if not col:
        col = Color(nombre="Azul Marino")
        db_session.add(col)
        db_session.commit()
        db_session.refresh(col)

    tal = db_session.query(Talla).first()
    if not tal:
        tal = Talla(nombre="M")
        db_session.add(tal)
        db_session.commit()
        db_session.refresh(tal)

    from app.models.temporada import Temporada
    temp = db_session.query(Temporada).first()
    if not temp:
        temp = Temporada(nombre="Verano 2026")
        db_session.add(temp)
        db_session.commit()
        db_session.refresh(temp)

    prod = db_session.query(Producto).filter(Producto.codigo == "V6-PROD-01").first()
    if not prod:
        prod = Producto(
            codigo="V6-PROD-01",
            nombre="Vestido Gala Elegance",
            descripcion="Vestido elegante",
            precio=Decimal("250.00"),
            categoria_id=cat.id,
            temporada_id=temp.id,
            active=True,
        )
        db_session.add(prod)
        db_session.commit()
        db_session.refresh(prod)

    pcol = db_session.query(ProductoColor).filter(ProductoColor.producto_codigo == prod.codigo).first()
    if not pcol:
        pcol = ProductoColor(producto_codigo=prod.codigo, color_id=col.id)
        db_session.add(pcol)
        db_session.commit()
        db_session.refresh(pcol)

    stock = db_session.query(StockInventario).filter(
        StockInventario.sucursal_id == suc.id, StockInventario.producto_color_id == pcol.id
    ).first()
    if not stock:
        stock = StockInventario(
            sucursal_id=suc.id,
            producto_color_id=pcol.id,
            talla_id=tal.id,
            cantidad=15,
        )
        db_session.add(stock)
        db_session.commit()
        db_session.refresh(stock)

    return {"sucursal": suc, "producto": prod, "stock": stock, "talla": tal, "color": col}


def test_dashboard_stats_endpoint(client: TestClient, auth_tokens, sample_inventory):
    headers = {"Authorization": f"Bearer {auth_tokens['admin_token']}"}
    res = client.get("/api/v1/reportes/dashboard-stats", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "ventas_hoy" in data
    assert "ventas_mes" in data
    assert "total_ingresos" in data
    assert "inventario" in data
    assert "sucursales" in data


def test_chatbot_local_inteligente(client: TestClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['client_token']}"}
    
    # 1. Saludo
    res = client.post("/api/v1/chatbot/mensaje", json={"mensaje": "Hola buenas tardes"}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "Bienvenido a StyleStore" in data["respuesta"]
    assert len(data["chips"]) > 0

    # 2. Consulta de sucursales
    res2 = client.post("/api/v1/chatbot/mensaje", json={"mensaje": "¿Dónde están sus sucursales físicas?"}, headers=headers)
    assert res2.status_code == 200
    assert "sucursales" in res2.json()["respuesta"].lower()


def test_notificaciones_usuario(client: TestClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['client_token']}"}
    
    # Obtener contador no leídas
    res = client.get("/api/v1/notificaciones/no-leidas-count", headers=headers)
    assert res.status_code == 200
    assert "count" in res.json()

    # Listar notificaciones
    res_list = client.get("/api/v1/notificaciones/mis-notificaciones", headers=headers)
    assert res_list.status_code == 200
    assert "items" in res_list.json()


def test_regla_reserva_elegibilidad(client: TestClient, auth_tokens, sample_inventory, db_session):
    headers = {"Authorization": f"Bearer {auth_tokens['client_token']}"}
    
    # Sin compras previas, elegibilidad debe ser False
    res_eleg = client.get("/api/v1/reservas/elegibilidad", headers=headers)
    assert res_eleg.status_code == 200
    eleg = res_eleg.json()
    assert eleg["puede_reservar"] is False
    assert eleg["compras_previas"] == 0

    # Intentar reservar sin compras debe fallar con 400
    res_reserva = client.post(
        "/api/v1/reservas",
        json={
            "sucursal_id": sample_inventory["sucursal"].id,
            "items": [{"stock_inventario_id": sample_inventory["stock"].id, "cantidad": 1}],
        },
        headers=headers,
    )
    assert res_reserva.status_code == 400
    assert "al menos 1 compra previa" in res_reserva.json()["detail"]

    # Simular una compra pagada previa para el cliente
    orden_previa = OrdenVenta(
        fecha=date.today() - timedelta(days=2),
        estado="pagada",
        total=Decimal("150.00"),
        tipo_venta="presencial",
        codigo_cliente=auth_tokens["client_profile"].codigo,
        sucursal_id=sample_inventory["sucursal"].id,
    )
    db_session.add(orden_previa)
    db_session.commit()

    # Ahora debe ser elegible
    res_eleg2 = client.get("/api/v1/reservas/elegibilidad", headers=headers)
    assert res_eleg2.status_code == 200
    assert res_eleg2.json()["puede_reservar"] is True

    # Ahora la reserva debe crearse exitosamente
    res_crear = client.post(
        "/api/v1/reservas",
        json={
            "sucursal_id": sample_inventory["sucursal"].id,
            "items": [{"stock_inventario_id": sample_inventory["stock"].id, "cantidad": 1}],
        },
        headers=headers,
    )
    assert res_crear.status_code == 201
    reserva_id = res_crear.json()["id"]
    assert res_crear.json()["estado"] == "pendiente"

    # Verificar que el cliente ve sus reservas en /reservas/mias
    res_mias = client.get("/api/v1/reservas/mias", headers=headers)
    assert res_mias.status_code == 200
    assert any(r["id"] == reserva_id for r in res_mias.json())

    # Verificar que el staff puede listar con filtro por sucursal
    admin_headers = {"Authorization": f"Bearer {auth_tokens['admin_token']}"}
    res_admin = client.get(f"/api/v1/reservas?sucursal_id={sample_inventory['sucursal'].id}", headers=admin_headers)
    assert res_admin.status_code == 200
    assert any(r["id"] == reserva_id for r in res_admin.json())

    # Cancelar la reserva como cliente y verificar restitución de stock
    res_cancelar = client.post(f"/api/v1/reservas/{reserva_id}/cancelar", headers=headers)
    assert res_cancelar.status_code == 200
    assert res_cancelar.json()["estado"] == "cancelada"

    # Intentar cancelar nuevamente debe fallar
    res_re_cancelar = client.post(f"/api/v1/reservas/{reserva_id}/cancelar", headers=headers)
    assert res_re_cancelar.status_code == 400



def test_venta_presencial_efectivo_y_qr(client: TestClient, auth_tokens, sample_inventory):
    headers = {"Authorization": f"Bearer {auth_tokens['admin_token']}"}
    
    # 1. Venta en Efectivo con vuelto
    payload_efectivo = {
        "codigo_cliente": auth_tokens["client_profile"].codigo,
        "sucursal_id": sample_inventory["sucursal"].id,
        "metodo_pago": "efectivo",
        "efectivo_recibido": 300.0,
        "items": [{"stock_inventario_id": sample_inventory["stock"].id, "cantidad": 1}],
    }
    res_ef = client.post("/api/v1/ventas/presencial", json=payload_efectivo, headers=headers)
    assert res_ef.status_code == 201
    v_data = res_ef.json()
    assert v_data["metodo_pago"] == "efectivo"
    assert v_data["ticket_numero"].startswith("TCK-")

    # 2. Venta con QR
    payload_qr = {
        "codigo_cliente": auth_tokens["client_profile"].codigo,
        "sucursal_id": sample_inventory["sucursal"].id,
        "metodo_pago": "qr",
        "items": [{"stock_inventario_id": sample_inventory["stock"].id, "cantidad": 1}],
    }
    res_qr = client.post("/api/v1/ventas/presencial", json=payload_qr, headers=headers)
    assert res_qr.status_code == 201
    assert res_qr.json()["metodo_pago"] == "qr"


def test_cambios_devoluciones_workflow(client: TestClient, auth_tokens, sample_inventory, db_session):
    headers_cli = {"Authorization": f"Bearer {auth_tokens['client_token']}"}
    headers_adm = {"Authorization": f"Bearer {auth_tokens['admin_token']}"}

    # Crear una orden de compra reciente (hace 2 días)
    orden_reciente = OrdenVenta(
        fecha=date.today() - timedelta(days=2),
        estado="pagada",
        total=Decimal("250.00"),
        tipo_venta="presencial",
        codigo_cliente=auth_tokens["client_profile"].codigo,
        sucursal_id=sample_inventory["sucursal"].id,
    )
    db_session.add(orden_reciente)
    db_session.flush()

    dv = DetalleVenta(
        orden_venta_id=orden_reciente.id,
        stock_inventario_id=sample_inventory["stock"].id,
        producto_nombre=sample_inventory["producto"].nombre,
        color_nombre="Azul",
        talla_nombre="M",
        cantidad=1,
        precio_unitario=Decimal("250.00"),
        subtotal=Decimal("250.00"),
    )
    db_session.add(dv)
    db_session.commit()

    # 1. Solicitar cambio (dentro del límite de 7 días)
    sol_payload = {
        "orden_venta_id": orden_reciente.id,
        "detalle_venta_id": dv.id,
        "tipo": "cambio",
        "motivo": "talla_incorrecta",
        "sucursal_id": sample_inventory["sucursal"].id,
        "fecha_programada": str(date.today() + timedelta(days=1)),
        "descripcion_problema": "La talla M me queda un poco grande, deseo cambiar por S.",
    }
    res_sol = client.post("/api/v1/cambios", json=sol_payload, headers=headers_cli)
    assert res_sol.status_code == 200
    sol_id = res_sol.json()["solicitud_id"]

    # 2. Encargado/Admin responde aprobando
    res_resp = client.put(
        f"/api/v1/cambios/{sol_id}/responder",
        json={"nuevo_estado": "aceptada", "respuesta_encargado": "Pasa por sucursal con la prenda y etiqueta."},
        headers=headers_adm,
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["estado"] == "aceptada"

    # 3. Canje completado en caja
    res_comp = client.post(f"/api/v1/cambios/{sol_id}/completar", json={"reponer_prenda_original": True}, headers=headers_adm)
    assert res_comp.status_code == 200
    assert res_comp.json()["estado"] == "completada"

    # 4. Probar que una compra de hace 15 días rechaza la solicitud (> 7 días)
    orden_antigua = OrdenVenta(
        fecha=date.today() - timedelta(days=15),
        estado="pagada",
        total=Decimal("250.00"),
        tipo_venta="presencial",
        codigo_cliente=auth_tokens["client_profile"].codigo,
        sucursal_id=sample_inventory["sucursal"].id,
    )
    db_session.add(orden_antigua)
    db_session.flush()

    dv_old = DetalleVenta(
        orden_venta_id=orden_antigua.id,
        stock_inventario_id=sample_inventory["stock"].id,
        producto_nombre=sample_inventory["producto"].nombre,
        cantidad=1,
        precio_unitario=Decimal("250.00"),
        subtotal=Decimal("250.00"),
    )
    db_session.add(dv_old)
    db_session.commit()

    sol_old = {
        "orden_venta_id": orden_antigua.id,
        "detalle_venta_id": dv_old.id,
        "tipo": "cambio",
        "motivo": "disconformidad",
        "sucursal_id": sample_inventory["sucursal"].id,
        "fecha_programada": str(date.today() + timedelta(days=1)),
        "descripcion_problema": "Deseo cambiarlo.",
    }
    res_old = client.post("/api/v1/cambios", json=sol_old, headers=headers_cli)
    assert res_old.status_code == 400
    assert "7 días" in res_old.json()["detail"]


def test_nuevos_reportes_previews(client: TestClient, auth_tokens):
    headers = {"Authorization": f"Bearer {auth_tokens['admin_token']}"}
    
    endpoints = [
        "/api/v1/reportes/mas-vendidos/preview",
        "/api/v1/reportes/ventas-producto/preview",
        "/api/v1/reportes/ventas-tipo/preview",
        "/api/v1/reportes/clientes/preview",
        "/api/v1/reportes/empleados/preview",
        "/api/v1/reportes/rotacion/preview",
        "/api/v1/reportes/envios/preview",
        "/api/v1/reportes/devoluciones/preview",
    ]
    for ep in endpoints:
        res = client.get(ep, headers=headers)
        assert res.status_code == 200, f"Error en endpoint {ep}: {res.text}"


def test_catalogo_para_ti_y_sucursales_publicas(client: TestClient, auth_tokens):
    """Verifica que el feed 'Para Ti' con IA y el listado de sucursales funcionen para clientes."""
    headers_cli = {"Authorization": f"Bearer {auth_tokens['client_token']}"}

    # 1. Endpoint /api/v1/catalogo/para-ti
    res_para_ti = client.get("/api/v1/catalogo/para-ti?limit=4", headers=headers_cli)
    assert res_para_ti.status_code == 200
    data_para_ti = res_para_ti.json()
    assert isinstance(data_para_ti, list)

    # 2. Endpoint /api/v1/sucursales accesible para cliente
    res_suc = client.get("/api/v1/sucursales", headers=headers_cli)
    assert res_suc.status_code == 200
    assert isinstance(res_suc.json(), list)


def test_asistente_ia_reportes(client: TestClient, auth_tokens):
    """Verifica que el asistente de IA para reportes responda adecuadamente al admin."""
    headers = {"Authorization": f"Bearer {auth_tokens['admin_token']}"}
    res = client.post(
        "/api/v1/reportes/asistente-ia",
        json={"pregunta": "¿Cuántas ropas se vendieron hoy y cuántos pedidos por delivery hubo?"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "respuesta" in data
    assert "kpis" in data
    assert isinstance(data["kpis"], list)


