"""Cobertura del módulo de reseñas por prenda."""
from decimal import Decimal

import pytest

from app.core.security import create_access_token
from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.color import Color
from app.models.empresa import Empresa
from app.models.orden_venta import DetalleVenta, OrdenVenta
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.stock_inventario import StockInventario
from app.models.sucursal import Sucursal
from app.models.talla import Talla
from app.models.temporada import Temporada
from app.models.user import User
from app.services.plan_service import PlanService


@pytest.fixture
def review_environment(db_session):
    empresa = db_session.query(Empresa).filter(Empresa.codigo == "stylestore").one()
    admin = User(
        empresa_id=empresa.id,
        email="review-admin@stylestore.test",
        name="Admin reseñas",
        hashed_password="hash",
        role="administrador",
        is_active=True,
    )
    client_user = User(
        empresa_id=empresa.id,
        email="review-client@stylestore.test",
        name="Ana",
        apellido="Mendoza",
        hashed_password="hash",
        role="cliente",
        is_active=True,
    )
    db_session.add_all([admin, client_user])
    db_session.flush()
    PlanService(db_session).contract(admin, "basico")
    profile = Cliente(codigo="CLI-REV-001", user_id=client_user.id, telefono="70000010", direccion="Calle Uno")
    category = Categoria(empresa_id=empresa.id, nombre="Reseñas Test")
    season = Temporada(empresa_id=empresa.id, nombre="Temporada Reseñas")
    color = Color(empresa_id=empresa.id, nombre="Azul Reseñas")
    size = Talla(empresa_id=empresa.id, nombre="R-M")
    branch = Sucursal(
        empresa_id=empresa.id,
        name="Sucursal Reseñas",
        city="Santa Cruz",
        address="Av. Reseñas 10",
        phone="33000010",
        active=True,
    )
    db_session.add_all([profile, category, season, color, size, branch])
    db_session.flush()
    product = Producto(
        codigo="REV-PROD-001",
        empresa_id=empresa.id,
        nombre="Prenda con comunidad",
        precio=Decimal("79.90"),
        categoria_id=category.id,
        temporada_id=season.id,
        active=True,
        visible_en_catalogo=True,
    )
    db_session.add(product)
    db_session.flush()
    product_color = ProductoColor(producto_codigo=product.codigo, color_id=color.id)
    db_session.add(product_color)
    db_session.flush()
    stock = StockInventario(
        producto_color_id=product_color.id,
        talla_id=size.id,
        sucursal_id=branch.id,
        cantidad=10,
    )
    db_session.add(stock)
    db_session.commit()
    token = create_access_token(data={"sub": str(client_user.id), "email": client_user.email, "role": "cliente"})
    return {
        "empresa": empresa,
        "user": client_user,
        "profile": profile,
        "product": product,
        "branch": branch,
        "stock": stock,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def test_client_can_publish_interest_and_update_single_review(client, review_environment):
    env = review_environment
    url = f"/api/v1/productos/{env['product'].codigo}/resenas/mia"
    created = client.put(url, json={"puntuacion": 4, "comentario": "Me gusta el diseño y quisiera comprarla."}, headers=env["headers"])
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["resumen"]["total"] == 1
    assert body["resumen"]["promedio"] == 4.0
    assert body["mi_resena"]["compra_verificada"] is False
    assert body["mi_resena"]["autor_nombre"] == "Ana Mendoza"

    updated = client.put(url, json={"puntuacion": 5, "comentario": "Ahora me encanta y combina con mi estilo."}, headers=env["headers"])
    assert updated.status_code == 200
    assert updated.json()["resumen"]["total"] == 1
    assert updated.json()["resumen"]["distribucion"]["5"] == 1


def test_review_becomes_verified_from_paid_order(client, db_session, review_environment):
    env = review_environment
    order = OrdenVenta(
        estado="pagada",
        total=Decimal("79.90"),
        tipo_venta="en linea",
        codigo_cliente=env["profile"].codigo,
        sucursal_id=env["branch"].id,
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(DetalleVenta(
        orden_venta_id=order.id,
        stock_inventario_id=env["stock"].id,
        producto_nombre=env["product"].nombre,
        cantidad=1,
        precio_unitario=Decimal("79.90"),
        subtotal=Decimal("79.90"),
    ))
    db_session.commit()

    response = client.put(
        f"/api/v1/productos/{env['product'].codigo}/resenas/mia",
        json={"puntuacion": 5, "comentario": "La tela y el acabado superaron mis expectativas."},
        headers=env["headers"],
    )
    assert response.status_code == 200, response.text
    assert response.json()["mi_resena"]["compra_verificada"] is True
    assert response.json()["resumen"]["compras_verificadas"] == 1


def test_rating_validation_delete_and_tenant_boundary(client, db_session, review_environment):
    env = review_environment
    url = f"/api/v1/productos/{env['product'].codigo}/resenas/mia"
    invalid = client.put(url, json={"puntuacion": 6, "comentario": "Fuera de rango"}, headers=env["headers"])
    assert invalid.status_code == 422

    client.put(url, json={"puntuacion": 3, "comentario": "Quisiera verla en más colores."}, headers=env["headers"])
    deleted = client.delete(url, headers=env["headers"])
    assert deleted.status_code == 200
    assert deleted.json()["resumen"]["total"] == 0

    other_company = Empresa(codigo="tenant-reviews-other", nombre="Tenant Reviews Other", active=True)
    db_session.add(other_company)
    db_session.flush()
    other_category = Categoria(empresa_id=other_company.id, nombre="Otra categoría")
    other_season = Temporada(empresa_id=other_company.id, nombre="Otra temporada")
    db_session.add_all([other_category, other_season])
    db_session.flush()
    other_product = Producto(
        codigo="REV-OTHER-001",
        empresa_id=other_company.id,
        nombre="Prenda ajena",
        precio=Decimal("50"),
        categoria_id=other_category.id,
        temporada_id=other_season.id,
        active=True,
        visible_en_catalogo=True,
    )
    db_session.add(other_product)
    db_session.commit()
    foreign = client.get(f"/api/v1/productos/{other_product.codigo}/resenas", headers=env["headers"])
    assert foreign.status_code == 404

