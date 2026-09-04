"""
Producto Service for Catalog and Inventory management.
"""
from sqlalchemy.orm import Session

from app.models.producto import Producto
from app.models.user import User
from app.schemas.producto import ProductoCreate, ProductoUpdate
from app.core.exceptions import NotFoundException
from app.services.bitacora_service import BitacoraService


class ProductoService:
    """Service for managing Products in the catalog."""

    def __init__(self, db: Session):
        self.db = db

    def list_productos(
        self,
        category: str | None = None,
        search: str | None = None,
        active_only: bool = False,
    ) -> list[Producto]:
        """List products with optional search and filters."""
        query = self.db.query(Producto)
        if active_only:
            query = query.filter(Producto.active == True)
        if category:
            query = query.filter(Producto.category.ilike(f"%{category}%"))
        if search:
            query = query.filter(
                (Producto.name.ilike(f"%{search}%"))
                | (Producto.description.ilike(f"%{search}%"))
                | (Producto.color.ilike(f"%{search}%"))
            )
        return query.order_by(Producto.name).all()

    def get_producto_by_id(self, producto_id: int) -> Producto:
        """Get product by ID."""
        producto = self.db.query(Producto).filter(Producto.id == producto_id).first()
        if not producto:
            raise NotFoundException(f"No se encontró el producto con ID {producto_id}.")
        return producto

    def create_producto(self, data: ProductoCreate, current_user: User) -> Producto:
        """Create a new product."""
        producto = Producto(
            name=data.name,
            description=data.description,
            category=data.category,
            size=data.size,
            color=data.color,
            price=data.price,
            stock=data.stock,
            active=data.active,
        )
        self.db.add(producto)
        self.db.commit()
        self.db.refresh(producto)

        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Creó el producto '{producto.name}' (Categoría: {producto.category}, Precio: ${producto.price})",
            module="productos",
        )
        return producto

    def update_producto(
        self, producto_id: int, data: ProductoUpdate, current_user: User
    ) -> Producto:
        """Update product details."""
        producto = self.get_producto_by_id(producto_id)

        if data.name is not None:
            producto.name = data.name
        if data.description is not None:
            producto.description = data.description
        if data.category is not None:
            producto.category = data.category
        if data.size is not None:
            producto.size = data.size
        if data.color is not None:
            producto.color = data.color
        if data.price is not None:
            producto.price = data.price
        if data.stock is not None:
            producto.stock = data.stock
        if data.active is not None:
            producto.active = data.active

        self.db.commit()
        self.db.refresh(producto)

        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Actualizó el producto '{producto.name}' (Stock: {producto.stock}, Precio: ${producto.price})",
            module="productos",
        )
        return producto

    def delete_producto(self, producto_id: int, current_user: User) -> dict:
        """Delete product."""
        producto = self.get_producto_by_id(producto_id)
        name = producto.name

        self.db.delete(producto)
        self.db.commit()

        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Eliminó el producto '{name}'",
            module="productos",
        )
        return {"message": f"Producto '{name}' eliminado correctamente."}
