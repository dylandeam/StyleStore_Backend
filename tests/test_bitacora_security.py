"""
Tests para la seguridad de la Bitácora de Auditoría:
- Contraseña predeterminada idéntica a la cuenta del usuario.
- Verificación de llave maestra / contraseña de cuenta.
- Registro y persistencia de la dirección IP en cada acción.
- Cambio de contraseña de bitácora desde el perfil verificando la contraseña actual.
- Restablecimiento de la contraseña a la predeterminada.
"""
import pytest
from fastapi.testclient import TestClient

from app.models.bitacora import Bitacora
from app.models.user import User


def test_bitacora_default_password_and_ip_tracking(client: TestClient, admin_token: str, db_session):
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "X-Forwarded-For": "192.168.1.150",
    }

    # 1. Consultar estado inicial (debe ser predeterminada)
    res = client.get("/api/v1/bitacora/estado-clave", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_custom"] is False

    # 2. Intentar desbloquear con contraseña errónea
    res = client.post(
        "/api/v1/bitacora/verificar-llave",
        json={"key": "clave_totalmente_incorrecta"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["valid"] is False

    # 3. Desbloquear con la contraseña predeterminada (Admin123!)
    res = client.post(
        "/api/v1/bitacora/verificar-llave",
        json={"key": "AdminPass123!"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["valid"] is True
    assert res.json()["ip"] == "192.168.1.150"

    # 4. Verificar que se haya registrado en la base de datos con la IP correcta
    ultimo_log = db_session.query(Bitacora).order_by(Bitacora.id.desc()).first()
    assert ultimo_log is not None
    assert ultimo_log.ip_address == "192.168.1.150"

    # 5. Listar bitácora y comprobar que el campo ip_address viene en la respuesta
    res = client.get("/api/v1/bitacora", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) > 0
    assert "ip_address" in items[0]
    assert items[0]["ip_address"] is not None


def test_bitacora_change_and_reset_password(client: TestClient, admin_token: str, db_session):
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "X-Forwarded-For": "200.87.140.22",
    }

    # 1. Intentar cambiar contraseña con contraseña actual incorrecta -> 400
    res = client.put(
        "/api/v1/bitacora/cambiar-clave",
        json={
            "current_password": "password_incorrecto",
            "new_bitacora_password": "NuevaClaveBitacora999!",
        },
        headers=headers,
    )
    assert res.status_code == 400

    # 2. Cambiar contraseña con contraseña actual correcta (Admin123!) -> 200
    res = client.put(
        "/api/v1/bitacora/cambiar-clave",
        json={
            "current_password": "AdminPass123!",
            "new_bitacora_password": "NuevaClaveBitacora999!",
        },
        headers=headers,
    )
    assert res.status_code == 200
    assert "exitosa" in res.json()["message"].lower()

    # 3. Estado de clave ahora debe ser personalizada
    res = client.get("/api/v1/bitacora/estado-clave", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_custom"] is True

    # 4. La contraseña anterior de la cuenta (Admin123!) ya NO debe desbloquear la bitácora
    res = client.post(
        "/api/v1/bitacora/verificar-llave",
        json={"key": "AdminPass123!"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["valid"] is False

    # 5. La nueva clave de bitácora SÍ debe desbloquear
    res = client.post(
        "/api/v1/bitacora/verificar-llave",
        json={"key": "NuevaClaveBitacora999!"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["valid"] is True
    assert res.json()["ip"] == "200.87.140.22"

    # 6. Restablecer clave a la predeterminada (verificando contraseña actual de cuenta)
    res = client.post(
        "/api/v1/bitacora/restablecer-clave",
        json={"current_password": "AdminPass123!"},
        headers=headers,
    )
    assert res.status_code == 200

    # 7. Comprobar que volvió al estado predeterminado
    res = client.get("/api/v1/bitacora/estado-clave", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_custom"] is False

    # 8. AdminPass123! vuelve a desbloquear la bitácora
    res = client.post(
        "/api/v1/bitacora/verificar-llave",
        json={"key": "AdminPass123!"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["valid"] is True
