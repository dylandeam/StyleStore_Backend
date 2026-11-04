"""Tenant-admin audit panel for offline synchronization (CU44)."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.core.security import hash_password
from app.models.empresa import Empresa
from app.models.notificacion import Notificacion
from app.models.reembolso_offline import ReembolsoOffline
from app.models.sucursal import Sucursal
from app.models.sync_operation import SyncOperation
from app.models.user import User
from app.services.notificacion_service import NotificacionService


def _tenant(db, label: str):
    suffix = uuid4().hex[:8]
    company = Empresa(codigo=f"{label}-{suffix}", nombre=f"Tenant {label} {suffix}", active=True)
    db.add(company)
    db.flush()
    admin = User(
        empresa_id=company.id,
        email=f"admin-{label}-{suffix}@example.com",
        name="Admin",
        apellido=label,
        ci=f"A-{suffix}",
        hashed_password=hash_password("TenantPass2026!"),
        role="administrador",
        is_active=True,
        is_platform_admin=False,
    )
    branch = Sucursal(
        empresa_id=company.id,
        name=f"Sucursal {label}",
        city="Santa Cruz",
        address="Av. Principal 100",
        phone="70000000",
        active=True,
    )
    db.add_all([admin, branch])
    db.commit()
    return company, admin, branch


def _login(client, user: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "TenantPass2026!"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_tenant_admin_panel_consolidates_conflict_refund_and_notification(client, db_session):
    company, admin, branch = _tenant(db_session, "cu44")
    operation_uuid = str(uuid4())
    operation = SyncOperation(
        operation_uuid=operation_uuid,
        empresa_id=company.id,
        user_id=admin.id,
        sucursal_id=branch.id,
        operation_type="venta_efectivo",
        payload_version=1,
        payload={"snapshot": {"total": 149.90, "moneda": "BOB"}},
        client_created_at=datetime.now(timezone.utc),
        status="conflicto",
        reason="Stock insuficiente al reconciliar la compra offline.",
    )
    db_session.add(operation)
    db_session.flush()
    refund = ReembolsoOffline(
        empresa_id=company.id,
        user_id=admin.id,
        sucursal_id=branch.id,
        sync_operation_id=operation.id,
        operation_uuid=operation_uuid,
        monto=Decimal("149.90"),
        moneda="BOB",
        metodo_original="efectivo",
        estado="pendiente",
        motivo="La prenda se agotó antes de sincronizar.",
    )
    result_notice = Notificacion(
        empresa_id=company.id,
        user_id=admin.id,
        tipo="resultado_operacion_offline",
        titulo="Compra no confirmada",
        mensaje="Se generó un reembolso.",
        url_accion=f"/cuenta/operaciones-pendientes?operation_uuid={operation_uuid}",
        leida=False,
    )
    db_session.add_all([refund, result_notice])
    db_session.commit()

    service = NotificacionService(db_session)
    assert service.notificar_incidente_operacion_offline(operation, refund) == 1
    assert service.notificar_incidente_operacion_offline(operation, refund) == 0

    response = client.get("/api/v1/sync/admin/operations", headers=_login(client, admin))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["operation_uuid"] == operation_uuid
    assert item["sucursal_nombre"] == branch.name
    assert item["resultado_notificado"] is True
    assert item["refund_id"] == refund.id
    assert item["refund_status"] == "pendiente"
    assert item["refund_amount"] == 149.9
    assert db_session.query(Notificacion).filter(
        Notificacion.user_id == admin.id,
        Notificacion.tipo == "incidente_operacion_offline",
    ).count() == 1


def test_admin_panel_is_tenant_scoped_and_rejects_customer(client, db_session):
    company_a, admin_a, branch_a = _tenant(db_session, "tenant-a")
    company_b, admin_b, branch_b = _tenant(db_session, "tenant-b")
    op_a = SyncOperation(
        operation_uuid=str(uuid4()), empresa_id=company_a.id, user_id=admin_a.id,
        sucursal_id=branch_a.id, operation_type="reserva", payload_version=1,
        payload={}, client_created_at=datetime.now(timezone.utc), status="confirmada",
        result_type="reserva", result_id=101,
    )
    op_b = SyncOperation(
        operation_uuid=str(uuid4()), empresa_id=company_b.id, user_id=admin_b.id,
        sucursal_id=branch_b.id, operation_type="resena_producto", payload_version=1,
        payload={}, client_created_at=datetime.now(timezone.utc), status="confirmada",
        result_type="resena_producto", result_id=202,
    )
    customer = User(
        empresa_id=company_a.id,
        email=f"customer-{uuid4().hex[:8]}@example.com",
        name="Cliente",
        apellido="CU44",
        ci=f"C-{uuid4().hex[:8]}",
        hashed_password=hash_password("TenantPass2026!"),
        role="cliente",
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add_all([op_a, op_b, customer])
    db_session.commit()

    response = client.get("/api/v1/sync/admin/operations", headers=_login(client, admin_a))
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["operation_uuid"] == op_a.operation_uuid

    forbidden = client.get("/api/v1/sync/admin/operations", headers=_login(client, customer))
    assert forbidden.status_code == 403
