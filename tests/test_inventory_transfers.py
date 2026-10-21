"""REQ-062: traspasos de inventario seguros entre sucursales."""
from decimal import Decimal
from uuid import uuid4

from app.core.security import create_access_token
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.empresa import Empresa
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.stock_inventario import StockInventario
from app.models.sucursal import Sucursal
from app.models.talla import Talla
from app.models.temporada import Temporada
from app.models.user import User
from app.services.plan_service import PlanService


def _scenario(db):
    suffix = uuid4().hex[:8]
    empresa = Empresa(codigo=f"trans-{suffix}", nombre=f"Transfer {suffix}", active=True)
    db.add(empresa)
    db.flush()
    admin = User(
        empresa_id=empresa.id,
        email=f"transfer-{suffix}@test.com",
        name="Admin Transfer",
        hashed_password="test",
        role="administrador",
        is_active=True,
    )
    source_branch = Sucursal(
        empresa_id=empresa.id, name=f"Origen {suffix}", city="La Paz",
        address="Origen 1", phone="70000001", active=True,
    )
    destination_branch = Sucursal(
        empresa_id=empresa.id, name=f"Destino {suffix}", city="El Alto",
        address="Destino 2", phone="70000002", active=True,
    )
    category = Categoria(empresa_id=empresa.id, nombre=f"Cat {suffix}")
    color = Color(empresa_id=empresa.id, nombre=f"Azul {suffix}")
    size = Talla(empresa_id=empresa.id, nombre=f"M-{suffix}")
    season = Temporada(empresa_id=empresa.id, nombre=f"Temp {suffix}")
    db.add_all([admin, source_branch, destination_branch, category, color, size, season])
    db.flush()
    product = Producto(
        empresa_id=empresa.id, codigo=f"TR-{suffix}", nombre="Chaqueta",
        precio=Decimal("250"), categoria_id=category.id, temporada_id=season.id, active=True,
    )
    db.add(product)
    db.flush()
    variant = ProductoColor(producto_codigo=product.codigo, color_id=color.id)
    db.add(variant)
    db.flush()
    source_stock = StockInventario(
        producto_color_id=variant.id, talla_id=size.id, sucursal_id=source_branch.id,
        cantidad=10, precio_variante=Decimal("275"), medidas={"pecho": 100},
    )
    db.add(source_stock)
    db.commit()
    PlanService(db).contract(admin, "basico")
    token = create_access_token(data={"sub": str(admin.id), "email": admin.email, "role": admin.role})
    return admin, token, source_branch, destination_branch, variant, size, source_stock


def test_transfer_is_idempotent_and_moves_stock_once(client, db_session):
    admin, token, origin, destination, variant, size, source_stock = _scenario(db_session)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "sucursal_origen_id": origin.id,
        "sucursal_destino_id": destination.id,
        "producto_color_id": variant.id,
        "talla_id": size.id,
        "cantidad": 4,
        "idempotency_key": str(uuid4()),
        "observacion": "Reposición de vitrina",
    }

    created = client.post("/api/v1/inventario/traspasos", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    transfer_id = created.json()["id"]
    repeated = client.post("/api/v1/inventario/traspasos", headers=headers, json=payload)
    assert repeated.status_code == 201, repeated.text
    assert repeated.json()["id"] == transfer_id

    approved = client.post(
        f"/api/v1/inventario/traspasos/{transfer_id}/aprobar",
        headers=headers,
        json={"respuesta": "Autorizado"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["estado"] == "aprobado"
    approved_again = client.post(
        f"/api/v1/inventario/traspasos/{transfer_id}/aprobar", headers=headers, json={}
    )
    assert approved_again.status_code == 200, approved_again.text

    db_session.refresh(source_stock)
    destination_stock = db_session.query(StockInventario).filter_by(
        producto_color_id=variant.id, talla_id=size.id, sucursal_id=destination.id
    ).one()
    assert source_stock.cantidad == 6
    assert destination_stock.cantidad == 4
    assert destination_stock.precio_variante == Decimal("275")
    assert destination_stock.medidas == {"pecho": 100}


def test_transfer_revalidates_stock_and_is_tenant_scoped(client, db_session):
    _, token, origin, destination, variant, size, source_stock = _scenario(db_session)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "sucursal_origen_id": origin.id,
        "sucursal_destino_id": destination.id,
        "producto_color_id": variant.id,
        "talla_id": size.id,
        "cantidad": 8,
        "idempotency_key": str(uuid4()),
    }
    created = client.post("/api/v1/inventario/traspasos", headers=headers, json=payload)
    assert created.status_code == 201, created.text

    source_stock.cantidad = 2
    db_session.commit()
    approved = client.post(
        f"/api/v1/inventario/traspasos/{created.json()['id']}/aprobar", headers=headers, json={}
    )
    assert approved.status_code == 409
    db_session.refresh(source_stock)
    assert source_stock.cantidad == 2

    other = Empresa(codigo=f"other-{uuid4().hex[:8]}", nombre="Otro tenant", active=True)
    db_session.add(other)
    db_session.flush()
    other_admin = User(
        empresa_id=other.id, email=f"other-{uuid4().hex[:8]}@test.com", name="Otro",
        hashed_password="test", role="administrador", is_active=True,
    )
    db_session.add(other_admin)
    db_session.commit()
    other_token = create_access_token(
        data={"sub": str(other_admin.id), "email": other_admin.email, "role": other_admin.role}
    )
    hidden = client.get("/api/v1/inventario/traspasos", headers={"Authorization": f"Bearer {other_token}"})
    assert hidden.status_code == 200
    assert hidden.json() == []
