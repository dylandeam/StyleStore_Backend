"""
Test suite for REQ-019: Plan tiers, branch limits, and AI capabilities enforcement.
Básico: max 2 sucursales, without chatbot/predicciones.
Intermedio: max 5 sucursales, with chatbot, without predicciones.
Profesional: max 10+ sucursales, with chatbot and predicciones.
"""
from app.models.user import User
from app.models.empresa import Empresa
from app.services.plan_service import PlanService


def _create_empresa(client, admin_token: str, codigo: str, email: str) -> dict:
    response = client.post(
        "/api/v1/empresas",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "codigo": codigo,
            "nombre": f"Empresa {codigo.upper()}",
            "admin_email": email,
            "admin_name": f"Admin {codigo.upper()}",
            "admin_password": "TenantPass2026!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _login(client, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TenantPass2026!"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_req019_basico_branch_limit_and_ai_blocking(client, db_session, admin_token):
    """
    REQ-019: Básico limits to 2 active branches, blocks chatbot and predicciones.
    """
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()

    company = _create_empresa(client, admin_token, "req019-basic", "admin@req019-basic.com")
    token = _login(client, "admin@req019-basic.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Verify contract exposes max_sucursales and capacidades
    contract_res = client.get("/api/v1/planes/mi-contratacion", headers=headers)
    assert contract_res.status_code == 200, contract_res.text
    contract_data = contract_res.json()
    assert contract_data["plan_codigo"] == "basico"
    assert contract_data["max_sucursales"] == 2
    assert contract_data["capacidades"]["chatbot"] is False
    assert contract_data["capacidades"]["predicciones"] is False

    # 2. Create Branch 1 (OK)
    b1_res = client.post(
        "/api/v1/sucursales",
        headers=headers,
        json={"name": "Sucursal Centro", "city": "La Paz", "address": "Av. 16 de Julio 100", "phone": "71111111"},
    )
    assert b1_res.status_code == 201, b1_res.text
    b1_id = b1_res.json()["id"]

    # 3. Create Branch 2 (OK)
    b2_res = client.post(
        "/api/v1/sucursales",
        headers=headers,
        json={"name": "Sucursal Sur", "city": "La Paz", "address": "Calle 21 de Calacoto 200", "phone": "72222222"},
    )
    assert b2_res.status_code == 201, b2_res.text

    # 4. Attempt to create Branch 3 (Forbidden by Básico quota)
    b3_res = client.post(
        "/api/v1/sucursales",
        headers=headers,
        json={"name": "Sucursal Sopocachi", "city": "La Paz", "address": "Plaza Abaroa 300", "phone": "73333333"},
    )
    assert b3_res.status_code == 403, b3_res.text
    assert "permite hasta 2 sucursales" in b3_res.json()["detail"]

    # 5. Deactivate Branch 1
    deactivate_res = client.put(
        f"/api/v1/sucursales/{b1_id}",
        headers=headers,
        json={"active": False},
    )
    assert deactivate_res.status_code == 200, deactivate_res.text
    assert deactivate_res.json()["active"] is False

    # 6. Now Branch 3 succeeds because active branches = 1
    b3_res_retry = client.post(
        "/api/v1/sucursales",
        headers=headers,
        json={"name": "Sucursal Sopocachi", "city": "La Paz", "address": "Plaza Abaroa 300", "phone": "73333333"},
    )
    assert b3_res_retry.status_code == 201, b3_res_retry.text

    # 7. Attempting to reactivate Branch 1 fails because active count would reach 3 (> 2)
    reactivate_fail = client.put(
        f"/api/v1/sucursales/{b1_id}",
        headers=headers,
        json={"active": True},
    )
    assert reactivate_fail.status_code == 403, reactivate_fail.text
    assert "permite hasta 2 sucursales" in reactivate_fail.json()["detail"]

    # 8. Chatbot is blocked
    chat_res = client.post(
        "/api/v1/chatbot/mensaje",
        headers=headers,
        json={"mensaje": "Hola chatbot"},
    )
    assert chat_res.status_code == 403, chat_res.text
    assert "chatbot" in chat_res.json()["detail"]

    # 9. Predicciones is blocked
    pred_res = client.get(
        "/api/v1/reportes/predicciones",
        headers=headers,
    )
    assert pred_res.status_code == 403, pred_res.text
    assert "predicciones" in pred_res.json()["detail"]


def test_req019_intermedio_plan_capabilities(client, db_session, admin_token):
    """
    REQ-019: Intermedio allows up to 5 branches, enables chatbot, blocks predicciones.
    """
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()

    company = _create_empresa(client, admin_token, "req019-mid", "admin@req019-mid.com")
    tenant_admin = db_session.query(User).filter(User.email == "admin@req019-mid.com").one()
    token = _login(client, "admin@req019-mid.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Contract Intermedio plan
    PlanService(db_session).contract(tenant_admin, "intermedio")

    contract_res = client.get("/api/v1/planes/mi-contratacion", headers=headers)
    assert contract_res.status_code == 200
    contract_data = contract_res.json()
    assert contract_data["plan_codigo"] == "intermedio"
    assert contract_data["max_sucursales"] == 5
    assert contract_data["capacidades"]["chatbot"] is True
    assert contract_data["capacidades"]["predicciones"] is False

    # Create 5 branches (all should succeed)
    for i in range(1, 6):
        res = client.post(
            "/api/v1/sucursales",
            headers=headers,
            json={"name": f"Sucursal Intermedia {i}", "city": "Cochabamba", "address": f"Av. América #{i}", "phone": f"7444444{i}"},
        )
        assert res.status_code == 201, res.text

    # 6th branch rejected (limit is 5)
    b6_res = client.post(
        "/api/v1/sucursales",
        headers=headers,
        json={"name": "Sucursal Intermedia 6", "city": "Cochabamba", "address": "Av. Heroínas 600", "phone": "74444446"},
    )
    assert b6_res.status_code == 403
    assert "permite hasta 5 sucursales" in b6_res.json()["detail"]

    # Chatbot allowed
    chat_res = client.post(
        "/api/v1/chatbot/mensaje",
        headers=headers,
        json={"mensaje": "Hola chatbot"},
    )
    assert chat_res.status_code == 200, chat_res.text

    # Predicciones still blocked
    pred_res = client.get(
        "/api/v1/reportes/predicciones",
        headers=headers,
    )
    assert pred_res.status_code == 403
    assert "predicciones" in pred_res.json()["detail"]


def test_req019_profesional_plan_capabilities(client, db_session, admin_token):
    """
    REQ-019: Profesional allows 10+ branches, enables chatbot AND predicciones ML.
    """
    platform_admin = db_session.query(User).filter(User.email == "admin_test@stylestore.com").one()
    platform_admin.is_platform_admin = True
    db_session.commit()

    company = _create_empresa(client, admin_token, "req019-pro", "admin@req019-pro.com")
    tenant_admin = db_session.query(User).filter(User.email == "admin@req019-pro.com").one()
    token = _login(client, "admin@req019-pro.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Contract Profesional plan
    PlanService(db_session).contract(tenant_admin, "profesional")

    contract_res = client.get("/api/v1/planes/mi-contratacion", headers=headers)
    assert contract_res.status_code == 200
    contract_data = contract_res.json()
    assert contract_data["plan_codigo"] == "profesional"
    assert contract_data["max_sucursales"] >= 10
    assert contract_data["capacidades"]["chatbot"] is True
    assert contract_data["capacidades"]["predicciones"] is True

    # Chatbot allowed
    chat_res = client.post(
        "/api/v1/chatbot/mensaje",
        headers=headers,
        json={"mensaje": "Hola chatbot"},
    )
    assert chat_res.status_code == 200, chat_res.text

    # Predicciones allowed
    pred_res = client.get(
        "/api/v1/reportes/predicciones",
        headers=headers,
    )
    assert pred_res.status_code == 200, pred_res.text
