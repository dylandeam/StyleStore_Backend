from decimal import Decimal

import pytest

from app.core.exceptions import BadRequestException
from app.models.categoria import Categoria
from app.models.color import Color
from app.models.empresa import Empresa
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.promocion import CodigoDescuento, PromocionAgrupada
from app.models.stock_inventario import StockInventario
from app.models.sucursal import Sucursal
from app.models.talla import Talla
from app.models.temporada import Temporada
from app.services.promocion_service import PromocionService


def _crear_stock(db_session, empresa, sufijo: str, precio="100.00"):
    categoria = Categoria(empresa_id=empresa.id, nombre=f"Categoria {sufijo}")
    temporada = Temporada(empresa_id=empresa.id, nombre=f"Temporada {sufijo}")
    color = Color(empresa_id=empresa.id, nombre=f"Color {sufijo}")
    talla = Talla(empresa_id=empresa.id, nombre=f"Talla {sufijo}")
    sucursal = Sucursal(empresa_id=empresa.id, name=f"Sucursal {sufijo}", city="SCZ", address="Centro", phone="70000000")
    db_session.add_all([categoria, temporada, color, talla, sucursal]); db_session.flush()
    producto = Producto(codigo=f"PRO-{sufijo}", empresa_id=empresa.id, nombre=f"Producto {sufijo}", precio=Decimal(precio), categoria_id=categoria.id, temporada_id=temporada.id)
    db_session.add(producto); db_session.flush()
    variante = ProductoColor(producto_codigo=producto.codigo, color_id=color.id)
    db_session.add(variante); db_session.flush()
    stock = StockInventario(producto_color_id=variante.id, talla_id=talla.id, sucursal_id=sucursal.id, cantidad=10)
    db_session.add(stock); db_session.flush()
    return stock, categoria, temporada


def test_aplica_mayor_promocion_agrupada_y_codigo_al_subtotal(db_session):
    empresa = db_session.query(Empresa).filter(Empresa.codigo == "stylestore").one()
    stock, categoria, temporada = _crear_stock(db_session, empresa, "PROMO")
    db_session.add_all([
        PromocionAgrupada(empresa_id=empresa.id, nombre="Categoría 10", tipo="categoria", categoria_id=categoria.id, porcentaje=10),
        PromocionAgrupada(empresa_id=empresa.id, nombre="Temporada 15", tipo="temporada", temporada_id=temporada.id, porcentaje=15),
        CodigoDescuento(empresa_id=empresa.id, codigo="EXTRA20", porcentaje=20),
    ])
    db_session.flush()

    resumen = PromocionService(db_session).calcular([(stock, 2)], empresa.id, "extra20", "online", consumir_codigo=True)

    assert resumen["subtotal_original"] == Decimal("200.00")
    assert resumen["descuento_promociones"] == Decimal("30.00")
    assert resumen["descuento_codigo"] == Decimal("34.00")
    assert resumen["total"] == Decimal("136.00")
    assert resumen["lineas"][0]["porcentaje_promocion"] == 15
    assert resumen["codigo_descuento"] == "EXTRA20"


def test_codigo_respeta_tenant_canal_y_limite(db_session):
    empresa = db_session.query(Empresa).filter(Empresa.codigo == "stylestore").one()
    otra = Empresa(codigo="otra-promo", nombre="Otra Promo")
    db_session.add(otra); db_session.flush()
    codigo = CodigoDescuento(empresa_id=empresa.id, codigo="CAJA", porcentaje=10, aplica_online=False, aplica_presencial=True, max_usos=1)
    db_session.add(codigo); db_session.flush()
    servicio = PromocionService(db_session)

    with pytest.raises(BadRequestException, match="línea"):
        servicio.validar_codigo(empresa.id, "CAJA", "online")
    with pytest.raises(BadRequestException, match="no existe"):
        servicio.validar_codigo(otra.id, "CAJA", "presencial")

    assert servicio.validar_codigo(empresa.id, "caja", "presencial").porcentaje == 10
    codigo.usos_actual = 1
    with pytest.raises(BadRequestException, match="límite"):
        servicio.validar_codigo(empresa.id, "CAJA", "presencial")
