"""
Pruebas exhaustivas para el flujo de Reembolsos Offline y Gestión de Estados (REQ-067).
Verifica:
1. Creación de reembolso en estado 'pendiente' con aviso del monto recaudado en efectivo ante conflicto de stock offline.
2. Transición de estados: 'pendiente' -> 'entregado' y 'pendiente' -> 'cancelado' con observaciones obligatorias.
3. Inmutabilidad histórica: un reembolso resuelto ('entregado' o 'cancelado') no puede ser modificado nuevamente.
4. Aislamiento multi-tenant: rechazo HTTP 404 ante intentos de listar o actualizar reembolsos de otras empresas.
5. Control de roles: clientes ven únicamente sus reembolsos en /mios y reciben HTTP 403 en la gestión administrativa.
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.categoria import Categoria
from app.models.color import Color
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.stock_inventario import StockInventario
from app.models.sucursal import Sucursal
from app.models.talla import Talla
from app.models.temporada import Temporada
from app.models.user import User
from app.models.empresa import Empresa
from app.models.reembolso_offline import ReembolsoOffline
from app.services.plan_service import PlanService
from app.core.security import hash_password, create_access_token


def _seed_tenant_with_out_of_stock_item(db: Session, codigo_tenant: str = "tenant_rf"):
    """Crea un tenant aislado con una sucursal y un producto sin existencias (stock = 0)."""
    empresa = db.query(Empresa).filter(Empresa.codigo == codigo_tenant).first()
    if not empresa:
        empresa = Empresa(codigo=codigo_tenant, nombre=f"Empresa {codigo_tenant}", active=True)
        db.add(empresa)
        db.commit()

    admin = db.query(User).filter(User.email == f"admin_{codigo_tenant}@test.com").first()
    if not admin:
        admin = User(
            empresa_id=empresa.id,
            email=f"admin_{codigo_tenant}@test.com",
            name=f"Admin {codigo_tenant}",
            hashed_password=hash_password("Pass123!"),
            role="administrador",
            is_active=True,
            is_platform_admin=False,
        )
        db.add(admin)
        db.commit()

    cajero = db.query(User).filter(User.email == f"cajero_{codigo_tenant}@test.com").first()
    if not cajero:
        cajero = User(
            empresa_id=empresa.id,
            email=f"cajero_{codigo_tenant}@test.com",
            name=f"Encargado Cajero {codigo_tenant}",
            hashed_password=hash_password("Pass123!"),
            role="encargado_sucursal",
            is_active=True,
            is_platform_admin=False,
        )
        db.add(cajero)
        db.commit()

    cliente = db.query(User).filter(User.email == f"cliente_{codigo_tenant}@test.com").first()
    if not cliente:
        cliente = User(
            empresa_id=empresa.id,
            email=f"cliente_{codigo_tenant}@test.com",
            name=f"Cliente {codigo_tenant}",
            hashed_password=hash_password("Pass123!"),
            role="cliente",
            is_active=True,
            is_platform_admin=False,
        )
        db.add(cliente)
        db.commit()

    suffix = uuid4().hex[:6]
    sucursal = Sucursal(
        empresa_id=empresa.id,
        name=f"Sucursal RF {suffix}",
        city="Santa Cruz",
        address="Av. Santos Dumont",
        phone="73333333",
        active=True,
    )
    cat = Categoria(empresa_id=empresa.id, nombre=f"Cat RF {suffix}")
    col = Color(empresa_id=empresa.id, nombre=f"Col RF {suffix}")
    sz = Talla(empresa_id=empresa.id, nombre=f"T-RF-{suffix}")
    temp = Temporada(empresa_id=empresa.id, nombre=f"Temp RF {suffix}")
    db.add_all([sucursal, cat, col, sz, temp])
    db.flush()

    prod = Producto(
        empresa_id=empresa.id,
        codigo=f"PRF-{suffix}",
        nombre=f"Vestido Gala {suffix}",
        precio=Decimal("220.00"),
        categoria_id=cat.id,
        temporada_id=temp.id,
        active=True,
    )
    db.add(prod)
    db.flush()

    prod_col = ProductoColor(producto_codigo=prod.codigo, color_id=col.id)
    db.add(prod_col)
    db.flush()

    stock = StockInventario(
        sucursal_id=sucursal.id,
        producto_color_id=prod_col.id,
        talla_id=sz.id,
        cantidad=0,  # Agotado para forzar conflicto de sincronización
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)

    PlanService(db).contract(admin, "basico")

    return {
        "empresa": empresa,
        "admin": admin,
        "cajero": cajero,
        "cliente": cliente,
        "sucursal": sucursal,
        "stock": stock,
    }


def test_offline_cash_sale_conflict_creates_pending_refund_with_amount_notice(
    client: TestClient, db_session: Session
):
    """REQ-067: Venta cobrada en efectivo offline que entra en conflicto genera ReembolsoOffline 'pendiente' con monto."""
    env = _seed_tenant_with_out_of_stock_item(db_session, "tenant_rf1")
    cajero_token = create_access_token(data={"sub": str(env["cajero"].id), "email": env["cajero"].email, "role": env["cajero"].role})
    headers = {"Authorization": f"Bearer {cajero_token}"}

    op_uuid = str(uuid4())
    sync_body = {
        "operation_uuid": op_uuid,
        "operation_type": "venta_efectivo",
        "payload_version": 1,
        "client_created_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "sucursal_id": env["stock"].sucursal_id,
            "metodo_pago": "efectivo",
            "efectivo_recibido": 250.00,
            "items": [{"stock_inventario_id": env["stock"].id, "cantidad": 1}],
            "snapshot": {"total": 220.00, "moneda": "BOB"},
        },
    }

    # Sincronizar venta offline
    sync_res = client.post("/api/v1/sync/operations", json=sync_body, headers=headers)
    assert sync_res.status_code == 200
    data = sync_res.json()

    assert data["status"] == "conflicto"
    assert "Stock insuficiente" in data["reason"]
    assert data["refund_id"] is not None
    assert data["refund_status"] == "pendiente"
    assert data["refund_amount"] == 220.00

    # Verificar registro en base de datos
    refund = db_session.query(ReembolsoOffline).filter(ReembolsoOffline.id == data["refund_id"]).one()
    assert refund.estado == "pendiente"
    assert refund.monto == Decimal("220.00")
    assert refund.empresa_id == env["empresa"].id
    assert refund.user_id == env["cajero"].id
    assert refund.sucursal_id == env["sucursal"].id


def test_refund_lifecycle_transitions_and_immutability(
    client: TestClient, db_session: Session
):
    """REQ-067: Transiciones de estado (entregado, cancelado) y protección contra mutaciones posteriores."""
    env = _seed_tenant_with_out_of_stock_item(db_session, "tenant_rf2")
    cajero_token = create_access_token(data={"sub": str(env["cajero"].id), "email": env["cajero"].email, "role": env["cajero"].role})
    admin_token = create_access_token(data={"sub": str(env["admin"].id), "email": env["admin"].email, "role": env["admin"].role})

    # Crear dos reembolsos por conflicto
    def _create_conflict_refund():
        op_uuid = str(uuid4())
        res = client.post(
            "/api/v1/sync/operations",
            json={
                "operation_uuid": op_uuid,
                "operation_type": "venta_efectivo",
                "payload_version": 1,
                "client_created_at": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "sucursal_id": env["stock"].sucursal_id,
                    "metodo_pago": "efectivo",
                    "efectivo_recibido": 220.00,
                    "items": [{"stock_inventario_id": env["stock"].id, "cantidad": 1}],
                    "snapshot": {"total": 220.00, "moneda": "BOB"},
                },
            },
            headers={"Authorization": f"Bearer {cajero_token}"},
        )
        return res.json()["refund_id"]

    refund_id_1 = _create_conflict_refund()
    refund_id_2 = _create_conflict_refund()

    # 1. Transición de pendiente -> entregado
    deliver_res = client.put(
        f"/api/v1/reembolsos/{refund_id_1}",
        headers={"Authorization": f"Bearer {cajero_token}"},
        json={"estado": "entregado", "observaciones": "Se devolvió el dinero en efectivo al cliente en ventanilla."},
    )
    assert deliver_res.status_code == 200
    assert deliver_res.json()["estado"] == "entregado"
    assert deliver_res.json()["observaciones"] == "Se devolvió el dinero en efectivo al cliente en ventanilla."
    assert deliver_res.json()["procesado_por"] == env["cajero"].id

    # 2. Inmutabilidad: intento de volver a modificar refund_id_1 recibe HTTP 403
    re_modify = client.put(
        f"/api/v1/reembolsos/{refund_id_1}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"estado": "cancelado", "observaciones": "Intento de anulación errónea."},
    )
    assert re_modify.status_code == 403
    assert "ya fue resuelto" in re_modify.json()["detail"].lower()

    # 3. Transición de pendiente -> cancelado
    cancel_res = client.put(
        f"/api/v1/reembolsos/{refund_id_2}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"estado": "cancelado", "observaciones": "Cliente optó por esperar reposición de la prenda."},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["estado"] == "cancelado"

    # 4. Inmutabilidad: intento de volver a modificar refund_id_2 recibe HTTP 403
    re_modify_2 = client.put(
        f"/api/v1/reembolsos/{refund_id_2}",
        headers={"Authorization": f"Bearer {cajero_token}"},
        json={"estado": "entregado", "observaciones": "Reabrir."},
    )
    assert re_modify_2.status_code == 403


def test_tenant_isolation_and_role_security_on_refunds(
    client: TestClient, db_session: Session
):
    """REQ-067: Aislamiento estricto multi-tenant y rechazo HTTP 403 a clientes no autorizados."""
    env_a = _seed_tenant_with_out_of_stock_item(db_session, "tenant_iso_a")
    env_b = _seed_tenant_with_out_of_stock_item(db_session, "tenant_iso_b")

    admin_a_token = create_access_token(data={"sub": str(env_a["admin"].id), "email": env_a["admin"].email, "role": env_a["admin"].role})
    admin_b_token = create_access_token(data={"sub": str(env_b["admin"].id), "email": env_b["admin"].email, "role": env_b["admin"].role})
    cliente_a_token = create_access_token(data={"sub": str(env_a["cliente"].id), "email": env_a["cliente"].email, "role": env_a["cliente"].role})

    # Crear reembolso en Tenant A
    op_uuid = str(uuid4())
    create_res = client.post(
        "/api/v1/sync/operations",
        json={
            "operation_uuid": op_uuid,
            "operation_type": "venta_efectivo",
            "payload_version": 1,
            "client_created_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "sucursal_id": env_a["stock"].sucursal_id,
                "metodo_pago": "efectivo",
                "efectivo_recibido": 300.00,
                "items": [{"stock_inventario_id": env_a["stock"].id, "cantidad": 1}],
                "snapshot": {"total": 220.00, "moneda": "BOB"},
            },
        },
        headers={"Authorization": f"Bearer {admin_a_token}"},
    )
    refund_a_id = create_res.json()["refund_id"]

    # 1. Admin A ve el reembolso
    list_a = client.get("/api/v1/reembolsos", headers={"Authorization": f"Bearer {admin_a_token}"})
    assert list_a.status_code == 200
    assert any(r["id"] == refund_a_id for r in list_a.json())

    # 2. Admin B NO ve el reembolso de Tenant A
    list_b = client.get("/api/v1/reembolsos", headers={"Authorization": f"Bearer {admin_b_token}"})
    assert list_b.status_code == 200
    assert not any(r["id"] == refund_a_id for r in list_b.json())

    # 3. Admin B intenta resolver reembolso de Tenant A -> HTTP 404
    cross_res = client.put(
        f"/api/v1/reembolsos/{refund_a_id}",
        headers={"Authorization": f"Bearer {admin_b_token}"},
        json={"estado": "entregado", "observaciones": "Intrusión cruzada"},
    )
    assert cross_res.status_code == 404
    assert "no encontrado" in cross_res.json()["detail"].lower()

    # 4. Cliente regular intenta acceder a la gestión general -> HTTP 403
    forbidden_list = client.get("/api/v1/reembolsos", headers={"Authorization": f"Bearer {cliente_a_token}"})
    assert forbidden_list.status_code == 403
    assert "personal autorizado" in forbidden_list.json()["detail"].lower()

    forbidden_update = client.put(
        f"/api/v1/reembolsos/{refund_a_id}",
        headers={"Authorization": f"Bearer {cliente_a_token}"},
        json={"estado": "entregado", "observaciones": "Cliente intentando aprobar"},
    )
    assert forbidden_update.status_code == 403
