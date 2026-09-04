"""
Pydantic schemas for Productos (Product Catalog & Inventory).
"""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class ProductoBase(BaseModel):
    """Base schema for Producto."""

    name: str = Field(..., min_length=2, max_length=150, description="Product name")
    description: str | None = Field(None, max_length=1000, description="Product description")
    category: str = Field(..., min_length=2, max_length=100, description="Product category (e.g. Ropa, Calzado, Accesorios)")
    size: str = Field(..., min_length=1, max_length=20, description="Product size (e.g. XS, S, M, L, XL, 38, 40)")
    color: str = Field(..., min_length=2, max_length=50, description="Color variant")
    price: Decimal = Field(..., gt=0, decimal_places=2, description="Unit price in local currency")
    stock: int = Field(default=0, ge=0, description="Available inventory count")
    active: bool = Field(default=True, description="Whether product is active for sale")


class ProductoCreate(ProductoBase):
    """Schema for creating a new product."""
    pass


class ProductoUpdate(BaseModel):
    """Schema for updating an existing product."""

    name: str | None = Field(None, min_length=2, max_length=150)
    description: str | None = Field(None, max_length=1000)
    category: str | None = Field(None, min_length=2, max_length=100)
    size: str | None = Field(None, min_length=1, max_length=20)
    color: str | None = Field(None, min_length=2, max_length=50)
    price: Decimal | None = Field(None, gt=0, decimal_places=2)
    stock: int | None = Field(None, ge=0)
    active: bool | None = None


class ProductoResponse(ProductoBase):
    """Schema for returning product details."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
