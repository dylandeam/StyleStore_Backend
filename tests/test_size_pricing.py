"""Regression coverage for authoritative product prices by size."""
from decimal import Decimal

from app.models.categoria import Categoria
from app.models.color import Color
from app.models.empresa import Empresa
from app.models.producto import Producto
from app.models.stock_inventario import StockInventario
from app.models.sucursal import Sucursal
from app.models.talla import Talla
from app.models.temporada import Temporada
from app.models.user import User
from app.schemas.producto import ProductoCreate, ProductoTallaPrecioInput
from app.services.producto_service import ProductoService
from app.services.promocion_service import PromocionService


def test_size_price_is_saved_and_used_by_checkout_calculator(db_session):
    empresa = db_session.query(Empresa).filter(Empresa.codigo == "stylestore").one()
    admin = User(
        empresa_id=empresa.id,
        email="size-pricing-admin@stylestore.test",
        name="Admin",
        apellido="Tallas",
        hashed_password="test",
        role="administrador",
        is_active=True,
    )
    category = Categoria(empresa_id=empresa.id, nombre="Precios por talla")
    season = Temporada(empresa_id=empresa.id, nombre="Temporada precios talla")
    color = Color(empresa_id=empresa.id, nombre="Azul precios talla")
    size_m = Talla(empresa_id=empresa.id, nombre="M-PRECIO")
    size_xxl = Talla(empresa_id=empresa.id, nombre="XXL-PRECIO")
    branch = Sucursal(
        empresa_id=empresa.id,
        name="Sucursal precios talla",
        city="Santa Cruz",
        address="Av. Tallas 100",
        phone="70000009",
        active=True,
    )
    db_session.add_all([admin, category, season, color, size_m, size_xxl, branch])
    db_session.commit()

    response = ProductoService(db_session).create_producto(
        ProductoCreate(
            codigo="PROD-SIZE-PRICE",
            nombre="Polera con precio por talla",
            precio=Decimal("70.00"),
            categoria_id=category.id,
            temporada_id=season.id,
            color_ids=[color.id],
            precios_talla=[
                ProductoTallaPrecioInput(talla_id=size_m.id, precio=Decimal("70.00")),
                ProductoTallaPrecioInput(talla_id=size_xxl.id, precio=Decimal("85.00")),
            ],
        ),
        current_user=admin,
    )

    assert {item.talla_nombre: item.precio for item in response.precios_talla} == {
        "M-PRECIO": Decimal("70.00"),
        "XXL-PRECIO": Decimal("85.00"),
    }

    product = db_session.query(Producto).filter(Producto.codigo == "PROD-SIZE-PRICE").one()
    stock = StockInventario(
        producto_color_id=product.colores_rel[0].id,
        talla_id=size_xxl.id,
        sucursal_id=branch.id,
        cantidad=5,
    )
    db_session.add(stock)
    db_session.commit()
    db_session.refresh(stock)

    original, final, percentage = PromocionService(db_session).precio_stock(stock)
    assert original == Decimal("85.00")
    assert final == Decimal("85.00")
    assert percentage == 0

    product.en_promocion = True
    product.porcentaje_descuento = 10
    db_session.commit()
    original, final, percentage = PromocionService(db_session).precio_stock(stock)
    assert original == Decimal("85.00")
    assert final == Decimal("76.50")
    assert percentage == 10

    stock.precio_variante = Decimal("90.00")
    db_session.commit()
    original, final, _ = PromocionService(db_session).precio_stock(stock)
    assert original == Decimal("90.00")
    assert final == Decimal("81.00")
