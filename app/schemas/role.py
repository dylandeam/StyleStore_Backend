"""
Pydantic schemas for Role and Permission management (RBAC).
"""
from pydantic import BaseModel, Field


class PermissionResponse(BaseModel):
    """Schema for returning permission details."""

    id: int
    code: str = Field(..., description="Unique permission code (e.g. sucursales.crear)")
    module: str = Field(..., description="Module group (e.g. sucursales)")
    description: str = Field(..., description="Human-readable description")

    model_config = {"from_attributes": True}


class RolePermissionsResponse(BaseModel):
    """Schema for returning a role with its assigned permissions."""

    role: str
    permissions: list[PermissionResponse]


class RoleItemResponse(BaseModel):
    """Schema for returning basic role information."""

    role: str
    permission_count: int


class UpdateRolePermissionsRequest(BaseModel):
    """Schema for updating the assigned permissions of a role."""

    permission_codes: list[str] = Field(
        ..., description="List of permission codes to assign to the role"
    )
