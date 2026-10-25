from io import BytesIO

from app.core.security import create_access_token
from app.models.empresa import Empresa
from app.models.proximamente import Proximamente
from app.models.prueba_virtual import PruebaVirtual
from app.models.categoria import Categoria
from app.models.temporada import Temporada
from app.models.producto import Producto
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.services.plan_service import PlanService


def _tenant_users(db_session):
    empresa = db_session.query(Empresa).filter(Empresa.codigo == "stylestore").one()
    admin = User(
        empresa_id=empresa.id,
        email="tenant-backup-admin@test.local",
        name="Administrador Tenant",
        hashed_password="hash",
        role="administrador",
        is_active=True,
        is_platform_admin=False,
    )
    cliente = User(
        empresa_id=empresa.id,
        email="tenant-upload-client@test.local",
        name="Cliente Tenant",
        hashed_password="hash",
        role="cliente",
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add_all([admin, cliente])
    db_session.flush()
    PlanService(db_session).contract(admin, "basico")
    db_session.commit()
    return empresa, admin, cliente


def _headers(user):
    token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role, "empresa_id": user.empresa_id}
    )
    return {"Authorization": f"Bearer {token}"}


def test_tenant_admin_cannot_access_global_backups(client, db_session):
    _, admin, _ = _tenant_users(db_session)

    for method, path in [
        ("get", "/api/v1/backups"),
        ("post", "/api/v1/backups/generar"),
        ("get", "/api/v1/backups/config"),
    ]:
        response = getattr(client, method)(path, headers=_headers(admin))
        assert response.status_code == 403
        assert "global" in response.json()["detail"].lower()


def test_upload_is_staff_only_and_persisted_with_tenant(client, db_session, tmp_path, monkeypatch):
    empresa, admin, cliente = _tenant_users(db_session)
    monkeypatch.chdir(tmp_path)
    image = ("foto.png", BytesIO(b"fake-png-content"), "image/png")

    denied = client.post(
        "/api/v1/uploads?folder=productos",
        headers=_headers(cliente),
        files={"file": image},
    )
    assert denied.status_code == 403

    allowed = client.post(
        "/api/v1/uploads?folder=productos",
        headers=_headers(admin),
        files={"file": ("foto.png", BytesIO(b"fake-png-content"), "image/png")},
    )
    assert allowed.status_code == 200, allowed.text
    filename = allowed.json()["filename"]
    assert filename.startswith(f"e{empresa.id}_")
    record = db_session.query(UploadedFile).filter(UploadedFile.filename == filename).one()
    assert record.empresa_id == empresa.id

    profile_upload = client.post(
        "/api/v1/uploads?folder=perfiles",
        headers=_headers(cliente),
        files={"file": ("avatar.gif", BytesIO(b"GIF89a-profile"), "image/gif")},
    )
    assert profile_upload.status_code == 200, profile_upload.text
    assert profile_upload.json()["url"].startswith("/uploads/perfiles/")
    profile_record = db_session.query(UploadedFile).filter(
        UploadedFile.filename == profile_upload.json()["filename"]
    ).one()
    assert profile_record.empresa_id == empresa.id


def test_proximamente_and_subscriptions_are_isolated_by_tenant(client, db_session):
    empresa_a, admin_a, cliente_a = _tenant_users(db_session)
    empresa_b = Empresa(codigo="tenant-secundario-b", nombre="Tenant Secundario B", active=True)
    db_session.add(empresa_b)
    db_session.flush()
    admin_b = User(
        empresa_id=empresa_b.id, email="admin-secundario-b@test.local", name="Admin B",
        hashed_password="hash", role="administrador", is_active=True,
    )
    db_session.add(admin_b)
    db_session.flush()
    PlanService(db_session).contract(admin_b, "basico")
    propio = Proximamente(empresa_id=empresa_a.id, nombre="Lanzamiento A", active=True)
    ajeno = Proximamente(empresa_id=empresa_b.id, nombre="Lanzamiento B", active=True)
    db_session.add_all([propio, ajeno])
    db_session.commit()

    listado = client.get("/api/v1/proximamente", headers=_headers(cliente_a))
    assert listado.status_code == 200
    assert [item["nombre"] for item in listado.json()] == ["Lanzamiento A"]

    detalle_ajeno = client.get(f"/api/v1/proximamente/{ajeno.id}", headers=_headers(cliente_a))
    assert detalle_ajeno.status_code == 404
    editar_ajeno = client.put(
        f"/api/v1/proximamente/{ajeno.id}", headers=_headers(admin_a), json={"nombre": "Intrusión"}
    )
    assert editar_ajeno.status_code == 404
    suscripcion_ajena = client.post(
        "/api/v1/notificaciones/suscribir-proximamente",
        headers=_headers(cliente_a),
        json={"proximamente_id": ajeno.id},
    )
    assert suscripcion_ajena.status_code == 404


def test_virtual_try_on_job_cannot_be_read_by_another_user_or_tenant(client, db_session):
    empresa_a, _, cliente_a = _tenant_users(db_session)
    empresa_b = Empresa(codigo="tenant-probador-b", nombre="Tenant Probador B", active=True)
    db_session.add(empresa_b)
    db_session.flush()
    cliente_b = User(
        empresa_id=empresa_b.id, email="cliente-probador-b@test.local", name="Cliente B",
        hashed_password="hash", role="cliente", is_active=True,
    )
    categoria = Categoria(empresa_id=empresa_b.id, nombre="Categoría Probador B")
    temporada = Temporada(empresa_id=empresa_b.id, nombre="Temporada Probador B")
    db_session.add_all([cliente_b, categoria, temporada])
    db_session.flush()
    producto = Producto(
        codigo="PROBADOR-B-001", empresa_id=empresa_b.id, nombre="Prenda privada",
        precio=100, categoria_id=categoria.id, temporada_id=temporada.id,
    )
    db_session.add(producto)
    db_session.flush()
    trabajo = PruebaVirtual(
        empresa_id=empresa_b.id,
        user_id=cliente_b.id,
        producto_codigo=producto.codigo,
        foto_persona_url="/uploads/pruebas/privada.png",
        foto_resultado_url="/uploads/pruebas/resultado.png",
        estado="completado",
    )
    db_session.add(trabajo)
    db_session.commit()

    response = client.get(f"/api/v1/prueba-virtual/{trabajo.id}", headers=_headers(cliente_a))
    assert response.status_code == 404
