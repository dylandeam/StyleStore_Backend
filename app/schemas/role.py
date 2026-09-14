"""
Pydantic schemas for Role and Permission management (RBAC).
Conforme a Especificación StyleStore v5.
"""
from datetime import datetime
from pydantic import BaseModel, Field


class PermissionResponse(BaseModel):
    """Schema for returning permission details."""

    id: int
    code: str = Field(..., description="Unique permission code (e.g. sucursales.crear)")
    module: str = Field(..., description="Module group (e.g. sucursales)")
    description: str = Field(..., description="Human-readable description")

    model_config = {"from_attributes": True}


class RoleItemResponse(BaseModel):
    """Schema for returning basic role information."""

    id: int
    nombre: str
    descripcion: str | None = None
    active: bool = True
    role: str  # Kept for backward compatibility
    permission_count: int
    user_count: int = 0
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class RoleCreateRequest(BaseModel):
    """Schema for creating a new role."""

    nombre: str = Field(..., min_length=2, max_length=100, description="Nombre único del rol")
    descripcion: str | None = Field(None, description="Descripción opcional del rol")


class RoleUpdateRequest(BaseModel):
    """Schema for updating an existing role."""

    nombre: str | None = Field(None, min_length=2, max_length=100)
    descripcion: str | None = None
    active: bool | None = None


class RolePermissionsResponse(BaseModel):
    """Schema for returning a role with its assigned permissions."""

    id: int | None = None
    nombre: str | None = None
    role: str
    permissions: list[PermissionResponse]


class UpdateRolePermissionsRequest(BaseModel):
    """Schema for updating the assigned permissions of a role."""

    permission_codes: list[str] = Field(
        ..., description="List of permission codes to assign to the role"
    )
