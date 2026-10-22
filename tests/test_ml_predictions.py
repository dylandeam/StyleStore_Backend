from decimal import Decimal

from app.core.security import create_access_token, hash_password
from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.models.orden_venta import OrdenVenta
from app.models.sucursal import Sucursal
from app.models.user import User
from app.services.ml_service import generate_synthetic_sales, train_supervised_model, train_unsupervised_model
from app.services.plan_service import PlanService


def test_synthetic_dataset_and_models_are_reproducible():
    assert generate_synthetic_sales(20) == generate_synthetic_sales(20)
    supervised = train_supervised_model()
    unsupervised = train_unsupervised_model()
    assert supervised["r2"] > 0.8
    assert supervised["mae"] < 60
    assert unsupervised["k"] == 3
    assert sum(unsupervised["distribucion_sintetica"].values()) == 120


def test_predictions_require_professional_plan_and_return_tenant_data(client, db_session):
    empresa = db_session.query(Empresa).filter(Empresa.codigo == "stylestore").one()
    admin = User(
        empresa_id=empresa.id,
        email="admin_ml@stylestore.com",
        name="Admin ML",
        hashed_password=hash_password("MlPass123!"),
        role="administrador",
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(admin)
    db_session.commit()
    token = create_access_token(data={"sub": str(admin.id), "email": admin.email, "role": admin.role})
    headers = {"Authorization": f"Bearer {token}"}
    PlanService(db_session).contract(admin, "basico")
    blocked = client.get("/api/v1/reportes/predicciones", headers=headers)
    assert blocked.status_code == 403
    assert "predicciones" in blocked.json()["detail"]
    PlanService(db_session).contract(admin, "profesional")
    own_branch = Sucursal(empresa_id=empresa.id, name="Sucursal ML Propia", city="La Paz", address="Calle 1", phone="70000001")
    other_company = Empresa(codigo="ml-ajena", nombre="ML Ajena", active=True)
    own_client_user = User(empresa_id=empresa.id, email="cliente_ml@stylestore.com", name="Cliente ML", hashed_password="hash", role="cliente", is_active=True)
    other_client_user = User(empresa_id=None, email="cliente_ml_ajeno@stylestore.com", name="Cliente Ajeno", hashed_password="hash", role="cliente", is_active=True)
    db_session.add_all([own_branch, other_company, own_client_user, other_client_user])
    db_session.flush()
    other_client_user.empresa_id = other_company.id
    other_branch = Sucursal(empresa_id=other_company.id, name="Sucursal ML Ajena", city="Oruro", address="Calle 2", phone="70000002")
    own_client = Cliente(codigo="CLI-ML-PROPIO", user_id=own_client_user.id, telefono="70000001", direccion="Calle 1")
    other_client = Cliente(codigo="CLI-ML-AJENO", user_id=other_client_user.id, telefono="70000002", direccion="Calle 2")
    db_session.add_all([other_branch, own_client, other_client])
    db_session.flush()
    db_session.add_all([
        OrdenVenta(codigo_cliente=own_client.codigo, sucursal_id=own_branch.id, total=Decimal("150"), estado="pagada", tipo_venta="presencial"),
        OrdenVenta(codigo_cliente=other_client.codigo, sucursal_id=other_branch.id, total=Decimal("9999"), estado="pagada", tipo_venta="presencial"),
    ])
    db_session.commit()
    response = client.get("/api/v1/reportes/predicciones", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["tenant_id"] == admin.empresa_id
    assert len(data["pronostico_7_dias"]) == 7
    assert set(data["segmentos_clientes"]) == {"ocasional", "frecuente", "alto_valor"}
    assert data["modelo_supervisado"]["seed"] == 20261021
    assert data["muestra_real_ordenes"] == 1
    assert data["clientes_analizados"] == 1
