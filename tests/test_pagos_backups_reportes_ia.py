"""
Tests de Pagos (PayPal / Caja POS), Backups con SHA-256, Reportes Excel/PDF, Detalle de Producto con IA local y Rastreo Yango.
"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models.producto import Producto
from app.models.categoria import Categoria
from app.models.temporada import Temporada
from app.models.orden_venta import OrdenVenta
from app.models.envio import Envio
from app.models.cliente import Cliente
from app.config import settings


from app.models.user import User
from app.core.security import hash_password


def _ensure_cliente(db_session, codigo="CLI-9999"):
    cli = db_session.query(Cliente).filter(Cliente.codigo == codigo).first()
    if not cli:
        # Crear usuario para el cliente
        email = f"user_{codigo.lower()}@stylestore.com"
        u = db_session.query(User).filter(User.email == email).first()
        if not u:
            u = User(
                email=email,
                name="Cliente Pruebas",
                hashed_password=hash_password("Pass123!"),
                role="cliente",
                is_active=True,
            )
            db_session.add(u)
            db_session.commit()

        cli = Cliente(
            codigo=codigo,
            user_id=u.id,
            telefono="77712345",
            direccion="Calle Falsa 123",
        )
        db_session.add(cli)
        db_session.commit()
    return cli


def test_catalogo_detalle_y_recomendados_ia(client: TestClient, admin_token: str, db_session):
    # 1. Crear categoría y temporada
    cat = db_session.query(Categoria).filter(Categoria.nombre == "Pantalones y Jeans Test").first()
    if not cat:
        cat = Categoria(nombre="Pantalones y Jeans Test")
        db_session.add(cat)
    temp = db_session.query(Temporada).filter(Temporada.nombre == "Invierno 2025 Test").first()
    if not temp:
        temp = Temporada(nombre="Invierno 2025 Test")
        db_session.add(temp)
    db_session.commit()

    # 2. Crear 2 productos afines
    p1 = db_session.query(Producto).filter(Producto.codigo == "PANT-VINT-01").first()
    if not p1:
        p1 = Producto(
            codigo="PANT-VINT-01",
            nombre="Pantalón de Tela Vintage Wide",
            descripcion="Pantalón retro clásico de tela de corte holgado",
            precio=Decimal("45.00"),
            categoria_id=cat.id,
            temporada_id=temp.id,
            active=True,
            visible_en_catalogo=True,
        )
        db_session.add(p1)

    p2 = db_session.query(Producto).filter(Producto.codigo == "PANT-VINT-02").first()
    if not p2:
        p2 = Producto(
            codigo="PANT-VINT-02",
            nombre="Pantalón de Tela Clásico Recto",
            descripcion="Pantalón de vestir retro elegante de tela fina",
            precio=Decimal("48.00"),
            categoria_id=cat.id,
            temporada_id=temp.id,
            active=True,
            visible_en_catalogo=True,
        )
        db_session.add(p2)
    db_session.commit()

    # Probar endpoint de detalle
    res_det = client.get(f"/api/v1/catalogo/{p1.codigo}/detalle")
    assert res_det.status_code == 200
    data_det = res_det.json()
    assert data_det["codigo"] == "PANT-VINT-01"
    assert data_det["categoria_nombre"] == "Pantalones y Jeans Test"

    # Probar recomendaciones de IA local
    res_rec = client.get(f"/api/v1/catalogo/{p1.codigo}/recomendados")
    assert res_rec.status_code == 200
    data_rec = res_rec.json()
    assert len(data_rec) >= 1
    assert data_rec[0]["codigo"] == "PANT-VINT-02"
    assert data_rec[0]["score_afinidad"] > 0.4
    assert "razon_recomendacion" in data_rec[0]


def test_caja_pos_y_paypal_flow(client: TestClient, admin_token: str, db_session):
    headers = {"Authorization": f"Bearer {admin_token}"}
    cli = _ensure_cliente(db_session, "CLI-9999")

    # 1. Crear orden de venta
    orden = OrdenVenta(
        codigo_cliente=cli.codigo,
        total=Decimal("100.00"),
        estado="pendiente",
        tipo_venta="presencial",
    )
    db_session.add(orden)
    db_session.commit()

    # 2. Probar Cobro en Caja con vuelto
    res_caja = client.post(
        "/api/v1/pagos/caja",
        json={"orden_venta_id": orden.id, "efectivo_recibido": 120.00},
        headers=headers,
    )
    assert res_caja.status_code == 200
    data_caja = res_caja.json()
    assert float(data_caja["cambio_devuelto"]) == 20.00
    assert "TKT-" in data_caja["ticket_numero"]

    # 3. Crear otra orden para PayPal
    orden2 = OrdenVenta(
        codigo_cliente=cli.codigo,
        total=Decimal("75.50"),
        estado="pendiente",
        tipo_venta="en_linea",
    )
    db_session.add(orden2)
    db_session.commit()

    # Crear orden PayPal
    res_pp_crear = client.post(
        "/api/v1/pagos/paypal/crear-orden",
        json={"orden_venta_id": orden2.id},
        headers=headers,
    )
    assert res_pp_crear.status_code == 200
    pp_order = res_pp_crear.json()
    assert "id" in pp_order

    # Capturar orden PayPal
    res_pp_cap = client.post(
        "/api/v1/pagos/paypal/capturar-orden",
        json={"orden_venta_id": orden2.id, "paypal_order_id": pp_order["id"]},
        headers=headers,
    )
    assert res_pp_cap.status_code == 200
    pago_cap = res_pp_cap.json()
    assert pago_cap["estado"] == "aprobado"


def test_backups_sha256_flow(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Generar backup
    res_gen = client.post("/api/v1/backups/generar", headers=headers)
    assert res_gen.status_code == 200
    b_data = res_gen.json()
    assert "sha256_hash" in b_data
    assert len(b_data["sha256_hash"]) == 64

    backup_id = b_data["id"]
    sha256 = b_data["sha256_hash"]

    # 2. Listar backups
    res_list = client.get("/api/v1/backups", headers=headers)
    assert res_list.status_code == 200
    assert any(b["id"] == backup_id for b in res_list.json())

    # 3. Verificar integridad
    res_ver = client.post(
        "/api/v1/backups/verificar",
        json={"id": backup_id, "expected_hash": sha256},
        headers=headers,
    )
    assert res_ver.status_code == 200
    assert res_ver.json()["es_valido"] is True

    # 4. Descargar backup
    res_dl = client.get(f"/api/v1/backups/{backup_id}/descargar", headers=headers)
    assert res_dl.status_code == 200
    assert len(res_dl.content) > 0

    # 5. Configuración automática de periodicidad
    res_cfg = client.get("/api/v1/backups/config", headers=headers)
    assert res_cfg.status_code == 200
    res_up_cfg = client.put(
        "/api/v1/backups/config",
        json={"auto_backup_enabled": True, "frequency_hours": 12, "retention_days": 15},
        headers=headers,
    )
    assert res_up_cfg.status_code == 200
    assert res_up_cfg.json()["frequency_hours"] == 12

    # 6. Restaurar desde el servidor
    res_rst = client.post(f"/api/v1/backups/{backup_id}/restaurar", headers=headers)
    if res_rst.status_code != 200:
        print("FAIL RESTORE DETAIL:", res_rst.status_code, res_rst.text)
    assert res_rst.status_code == 200
    assert res_rst.json()["success"] is True

    # 7. Subir archivo JSON y restaurar
    res_upload_rst = client.post(
        "/api/v1/backups/subir-restaurar",
        files={"file": ("backup_test.json", res_dl.content, "application/json")},
        headers=headers,
    )
    if res_upload_rst.status_code != 200:
        print("FAIL UPLOAD RESTORE DETAIL:", res_upload_rst.status_code, res_upload_rst.text)
    assert res_upload_rst.status_code == 200
    assert res_upload_rst.json()["success"] is True


def test_reportes_excel_pdf(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Exportar Ventas Excel
    res_v_xl = client.get("/api/v1/reportes/ventas/excel", headers=headers)
    assert res_v_xl.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res_v_xl.headers["content-type"]

    # 2. Exportar Ventas PDF
    res_v_pdf = client.get("/api/v1/reportes/ventas/pdf", headers=headers)
    assert res_v_pdf.status_code == 200
    assert "application/pdf" in res_v_pdf.headers["content-type"]

    # 3. Exportar Inventario Excel
    res_i_xl = client.get("/api/v1/reportes/inventario/excel", headers=headers)
    assert res_i_xl.status_code == 200

    # 4. Exportar Inventario PDF
    res_i_pdf = client.get("/api/v1/reportes/inventario/pdf", headers=headers)
    assert res_i_pdf.status_code == 200


def test_bitacora_verificar_llave(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Llave correcta
    res_ok = client.post(
        "/api/v1/bitacora/verificar-llave",
        json={"key": settings.ADMIN_MASTER_KEY},
        headers=headers,
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["valid"] is True

    # Llave incorrecta
    res_fail = client.post(
        "/api/v1/bitacora/verificar-llave",
        json={"key": "ClaveIncorrecta123!"},
        headers=headers,
    )
    assert res_fail.status_code == 200
    assert res_fail.json()["valid"] is False


def test_envio_yango_tracking(client: TestClient, admin_token: str, db_session):
    headers = {"Authorization": f"Bearer {admin_token}"}
    cli = _ensure_cliente(db_session, "CLI-8888")

    orden = OrdenVenta(codigo_cliente=cli.codigo, total=Decimal("50.00"), estado="pagada")
    db_session.add(orden)
    db_session.commit()

    envio = Envio(
        orden_venta_id=orden.id,
        direccion="Av. San Martín #450",
        ciudad="Santa Cruz",
        costo=Decimal("15.00"),
        estado="pendiente",
    )
    db_session.add(envio)
    db_session.commit()

    # Actualizar tracking Yango puesto a mano por el encargado
    res_yango = client.patch(
        f"/api/v1/envios/{envio.id}/yango",
        json={
            "yango_tracking_code": "YANGO-SCZ-8892",
            "yango_tracking_url": "https://yango.delivery/track/YANGO-SCZ-8892",
            "delivery_conductor": "Carlos Mendoza (Moto Honda CB125)",
            "estado": "en camino",
        },
        headers=headers,
    )
    assert res_yango.status_code == 200
    d_yango = res_yango.json()
    assert d_yango["yango_tracking_code"] == "YANGO-SCZ-8892"
    assert d_yango["delivery_conductor"] == "Carlos Mendoza (Moto Honda CB125)"
    assert d_yango["estado"] == "en camino"

    # Consultar por orden
    res_cli = client.get(f"/api/v1/envios/orden/{orden.id}", headers=headers)
    assert res_cli.status_code == 200
    assert res_cli.json()["yango_tracking_code"] == "YANGO-SCZ-8892"
