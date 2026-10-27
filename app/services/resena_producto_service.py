"""Reglas de negocio de reseñas, compra verificada y aislamiento multitenant."""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.cliente import Cliente
from app.models.orden_venta import DetalleVenta, OrdenVenta
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.resena_producto import ResenaProducto
from app.models.stock_inventario import StockInventario
from app.models.user import User
from app.schemas.resena_producto import ResenaProductoUpsert
from app.services.tenant_scope import effective_empresa_id


VALID_PURCHASE_STATES = ("pagada", "en_camino", "entregada")


class ResenaProductoService:
    def __init__(self, db: Session):
        self.db = db

    def _get_product(self, codigo: str, current_user: User | None) -> Producto:
        query = self.db.query(Producto).filter(
            func.lower(Producto.codigo) == codigo.strip().lower(),
            Producto.active.is_(True),
        )
        if current_user:
            scoped_empresa = effective_empresa_id(current_user)
            if scoped_empresa is not None:
                query = query.filter(Producto.empresa_id == scoped_empresa)
        product = query.first()
        if not product or product.empresa_id is None:
            raise NotFoundException("La prenda no existe en el tenant seleccionado")
        return product

    def _verified_user_ids(self, product: Producto, user_ids: list[int]) -> set[int]:
        if not user_ids:
            return set()
        rows = (
            self.db.query(Cliente.user_id)
            .join(OrdenVenta, OrdenVenta.codigo_cliente == Cliente.codigo)
            .join(DetalleVenta, DetalleVenta.orden_venta_id == OrdenVenta.id)
            .join(StockInventario, StockInventario.id == DetalleVenta.stock_inventario_id)
            .join(ProductoColor, ProductoColor.id == StockInventario.producto_color_id)
            .filter(
                Cliente.user_id.in_(user_ids),
                OrdenVenta.estado.in_(VALID_PURCHASE_STATES),
                ProductoColor.producto_codigo == product.codigo,
                OrdenVenta.sucursal.has(empresa_id=product.empresa_id),
            )
            .distinct()
            .all()
        )
        return {int(row[0]) for row in rows}

    @staticmethod
    def _serialize(review: ResenaProducto, verified: set[int], current_user: User | None) -> dict:
        author = review.user
        full_name = " ".join(part for part in (author.name, author.apellido) if part).strip()
        return {
            "id": review.id,
            "puntuacion": review.puntuacion,
            "comentario": review.comentario,
            "autor_nombre": full_name or "Cliente StyleStore",
            "autor_foto": author.foto,
            "compra_verificada": review.user_id in verified,
            "es_propia": bool(current_user and review.user_id == current_user.id),
            "created_at": review.created_at,
            "updated_at": review.updated_at,
        }

    def list_for_product(self, codigo: str, current_user: User | None) -> dict:
        product = self._get_product(codigo, current_user)
        reviews = (
            self.db.query(ResenaProducto)
            .filter(
                ResenaProducto.empresa_id == product.empresa_id,
                ResenaProducto.producto_codigo == product.codigo,
                ResenaProducto.active.is_(True),
            )
            .order_by(ResenaProducto.updated_at.desc(), ResenaProducto.id.desc())
            .limit(100)
            .all()
        )
        verified = self._verified_user_ids(product, [review.user_id for review in reviews])
        items = [self._serialize(review, verified, current_user) for review in reviews]
        total = len(items)
        distribution = {score: 0 for score in range(1, 6)}
        for item in items:
            distribution[item["puntuacion"]] += 1
        average = round(sum(item["puntuacion"] for item in items) / total, 1) if total else 0.0
        own = next((item for item in items if item["es_propia"]), None)
        return {
            "producto_codigo": product.codigo,
            "resumen": {
                "promedio": average,
                "total": total,
                "compras_verificadas": sum(1 for item in items if item["compra_verificada"]),
                "distribucion": distribution,
            },
            "resenas": items,
            "mi_resena": own,
            "puede_comentar": bool(current_user and current_user.role == "cliente" and not current_user.is_platform_admin),
        }

    def upsert(self, codigo: str, payload: ResenaProductoUpsert, current_user: User) -> dict:
        if current_user.role != "cliente" or current_user.is_platform_admin:
            raise ForbiddenException("Solo los clientes pueden publicar reseñas de prendas")
        product = self._get_product(codigo, current_user)
        review = self.db.query(ResenaProducto).filter(
            ResenaProducto.empresa_id == product.empresa_id,
            ResenaProducto.producto_codigo == product.codigo,
            ResenaProducto.user_id == current_user.id,
        ).first()
        if review:
            review.puntuacion = payload.puntuacion
            review.comentario = payload.comentario
            review.active = True
        else:
            review = ResenaProducto(
                empresa_id=product.empresa_id,
                producto_codigo=product.codigo,
                user_id=current_user.id,
                puntuacion=payload.puntuacion,
                comentario=payload.comentario,
            )
            self.db.add(review)
        self.db.commit()
        return self.list_for_product(product.codigo, current_user)

    def delete_own(self, codigo: str, current_user: User) -> dict:
        product = self._get_product(codigo, current_user)
        review = self.db.query(ResenaProducto).filter(
            ResenaProducto.empresa_id == product.empresa_id,
            ResenaProducto.producto_codigo == product.codigo,
            ResenaProducto.user_id == current_user.id,
            ResenaProducto.active.is_(True),
        ).first()
        if not review:
            raise NotFoundException("Todavía no publicaste una reseña de esta prenda")
        review.active = False
        self.db.commit()
        return self.list_for_product(product.codigo, current_user)

