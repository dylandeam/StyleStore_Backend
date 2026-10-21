from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException
from app.models.promocion import CodigoDescuento, PromocionAgrupada


CENT = Decimal("0.01")


class PromocionService:
    """Calculadora autoritativa. Las promociones agrupadas no se acumulan: gana el porcentaje mayor."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return value.quantize(CENT, rounding=ROUND_HALF_UP)

    def porcentaje_producto(self, producto) -> int:
        hoy = date.today()
        directo = int(producto.porcentaje_descuento or 0) if producto.en_promocion else 0
        query = self.db.query(PromocionAgrupada).filter(
            PromocionAgrupada.empresa_id == producto.empresa_id,
            PromocionAgrupada.active.is_(True),
            or_(PromocionAgrupada.fecha_inicio.is_(None), PromocionAgrupada.fecha_inicio <= hoy),
            or_(PromocionAgrupada.fecha_fin.is_(None), PromocionAgrupada.fecha_fin >= hoy),
            or_(
                and_(PromocionAgrupada.tipo == "categoria", PromocionAgrupada.categoria_id == producto.categoria_id),
                and_(PromocionAgrupada.tipo == "temporada", PromocionAgrupada.temporada_id == producto.temporada_id),
            ),
        )
        agrupado = max((p.porcentaje for p in query.all()), default=0)
        return max(directo, agrupado)

    def precio_stock(self, stock) -> tuple[Decimal, Decimal, int]:
        producto = stock.producto_color.producto
        original = Decimal(stock.precio_variante if stock.precio_variante is not None else producto.precio)
        porcentaje = self.porcentaje_producto(producto)
        precio = self._money(original * (Decimal(100 - porcentaje) / Decimal(100)))
        return original, precio, porcentaje

    def validar_codigo(self, empresa_id: int | None, codigo: str | None, canal: str, *, lock: bool = False) -> CodigoDescuento | None:
        if not codigo:
            return None
        if not empresa_id:
            raise BadRequestException("No se pudo determinar el tenant del código de descuento.")
        hoy = date.today()
        query = self.db.query(CodigoDescuento).filter(
            CodigoDescuento.empresa_id == empresa_id,
            CodigoDescuento.codigo == codigo.strip().upper(),
            CodigoDescuento.active.is_(True),
        )
        if lock:
            query = query.with_for_update(of=CodigoDescuento)
        item = query.first()
        if not item:
            raise BadRequestException("El código de descuento no existe o está inactivo.")
        if item.fecha_inicio and item.fecha_inicio > hoy:
            raise BadRequestException("El código de descuento todavía no está vigente.")
        if item.fecha_fin and item.fecha_fin < hoy:
            raise BadRequestException("El código de descuento venció.")
        if canal == "online" and not item.aplica_online:
            raise BadRequestException("El código no está habilitado para compras en línea.")
        if canal == "presencial" and not item.aplica_presencial:
            raise BadRequestException("El código no está habilitado para compras presenciales.")
        if item.max_usos is not None and item.usos_actual >= item.max_usos:
            raise BadRequestException("El código alcanzó su límite de usos.")
        return item

    def calcular(self, stocks_cantidades, empresa_id: int | None, codigo: str | None, canal: str, *, consumir_codigo: bool = False):
        subtotal_original = Decimal("0.00")
        subtotal_promocional = Decimal("0.00")
        lineas = []
        for stock, cantidad in stocks_cantidades:
            original, precio, porcentaje = self.precio_stock(stock)
            subtotal_original += original * cantidad
            subtotal = self._money(precio * cantidad)
            subtotal_promocional += subtotal
            lineas.append({"stock": stock, "cantidad": cantidad, "precio_original": original, "precio_unitario": precio, "porcentaje_promocion": porcentaje, "subtotal": subtotal})
        cupon = self.validar_codigo(empresa_id, codigo, canal, lock=consumir_codigo)
        porcentaje_codigo = cupon.porcentaje if cupon else 0
        descuento_codigo = self._money(subtotal_promocional * Decimal(porcentaje_codigo) / Decimal(100))
        total = self._money(subtotal_promocional - descuento_codigo)
        if cupon and consumir_codigo:
            cupon.usos_actual += 1
        return {
            "lineas": lineas,
            "subtotal_original": self._money(subtotal_original),
            "descuento_promociones": self._money(subtotal_original - subtotal_promocional),
            "subtotal_promocional": self._money(subtotal_promocional),
            "descuento_codigo": descuento_codigo,
            "total": total,
            "codigo_descuento": cupon.codigo if cupon else None,
            "porcentaje_codigo": porcentaje_codigo,
        }
