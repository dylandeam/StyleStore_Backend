"""
Role and Permission Service (RBAC).
"""
from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user import User
from app.core.exceptions import NotFoundException
from app.services.bitacora_service import BitacoraService

AVAILABLE_ROLES = ["administrador", "encargado_sucursal", "cajero", "cliente"]

BASE_PERMISSIONS = [
    # Usuarios
    {"code": "usuarios.crear", "module": "usuarios", "description": "Crear y registrar empleados o usuarios"},
    {"code": "usuarios.ver", "module": "usuarios", "description": "Visualizar listado y detalle de usuarios"},
    # Empleados (CU8)
    {"code": "empleados.crear", "module": "empleados", "description": "Registrar nuevos empleados"},
    {"code": "empleados.editar", "module": "empleados", "description": "Editar datos de empleados"},
    {"code": "empleados.eliminar", "module": "empleados", "description": "Eliminar empleados"},
    {"code": "empleados.ver", "module": "empleados", "description": "Visualizar listado de empleados"},
    # Clientes (CU9)
    {"code": "clientes.crear", "module": "clientes", "description": "Registrar nuevos clientes"},
    {"code": "clientes.editar", "module": "clientes", "description": "Editar datos de clientes"},
    {"code": "clientes.eliminar", "module": "clientes", "description": "Eliminar clientes"},
    {"code": "clientes.ver", "module": "clientes", "description": "Visualizar listado de clientes"},
    # Sucursales (CU7)
    {"code": "sucursales.crear", "module": "sucursales", "description": "Crear nuevas sucursales"},
    {"code": "sucursales.editar", "module": "sucursales", "description": "Editar información de sucursales"},
    {"code": "sucursales.eliminar", "module": "sucursales", "description": "Eliminar o desactivar sucursales"},
    {"code": "sucursales.ver", "module": "sucursales", "description": "Visualizar sucursales"},
    # Categorías (CU11)
    {"code": "categorias.crear", "module": "categorias", "description": "Crear categorías de prendas"},
    {"code": "categorias.editar", "module": "categorias", "description": "Editar categorías"},
    {"code": "categorias.eliminar", "module": "categorias", "description": "Eliminar categorías"},
    {"code": "categorias.ver", "module": "categorias", "description": "Visualizar categorías"},
    # Colores (CU12)
    {"code": "colores.crear", "module": "colores", "description": "Crear colores de prendas"},
    {"code": "colores.editar", "module": "colores", "description": "Editar colores"},
    {"code": "colores.eliminar", "module": "colores", "description": "Eliminar colores"},
    {"code": "colores.ver", "module": "colores", "description": "Visualizar colores"},
    # Tallas (CU13)
    {"code": "tallas.crear", "module": "tallas", "description": "Crear tallas de prendas"},
    {"code": "tallas.editar", "module": "tallas", "description": "Editar tallas"},
    {"code": "tallas.eliminar", "module": "tallas", "description": "Eliminar tallas"},
    {"code": "tallas.ver", "module": "tallas", "description": "Visualizar tallas"},
    # Temporadas (CU14)
    {"code": "temporadas.crear", "module": "temporadas", "description": "Crear temporadas de prendas"},
    {"code": "temporadas.editar", "module": "temporadas", "description": "Editar temporadas"},
    {"code": "temporadas.eliminar", "module": "temporadas", "description": "Eliminar temporadas"},
    {"code": "temporadas.ver", "module": "temporadas", "description": "Visualizar temporadas"},
    # Productos (CU10 / CU17)
    {"code": "productos.crear", "module": "productos", "description": "Crear nuevos productos en catálogo"},
    {"code": "productos.editar", "module": "productos", "description": "Editar información y stock de productos"},
    {"code": "productos.eliminar", "module": "productos", "description": "Eliminar o desactivar productos"},
    {"code": "productos.ver", "module": "productos", "description": "Visualizar catálogo de productos"},
    # Proveedores (CU16)
    {"code": "proveedores.crear", "module": "proveedores", "description": "Registrar nuevos proveedores"},
    {"code": "proveedores.editar", "module": "proveedores", "description": "Editar información de proveedores"},
    {"code": "proveedores.eliminar", "module": "proveedores", "description": "Eliminar proveedores"},
    {"code": "proveedores.ver", "module": "proveedores", "description": "Visualizar proveedores"},
    # Auditoria y Roles
    {"code": "bitacora.ver", "module": "bitacora", "description": "Visualizar historial de auditoría y bitácora"},
    {"code": "roles.gestionar", "module": "roles", "description": "Gestionar roles y asignación de permisos"},
]


class RoleService:
    """Service for managing RBAC roles and permissions."""

    def __init__(self, db: Session):
        self.db = db

    def seed_default_permissions_and_roles(self):
        """Seed base permissions and assign all to administrator."""
        # Ensure all base permissions exist
        for perm_data in BASE_PERMISSIONS:
            existing = self.db.query(Permission).filter(Permission.code == perm_data["code"]).first()
            if not existing:
                perm = Permission(
                    code=perm_data["code"],
                    module=perm_data["module"],
                    description=perm_data["description"],
                )
                self.db.add(perm)
        self.db.commit()

        # Ensure all permissions are assigned to administrador role
        all_perms = self.db.query(Permission).all()
        for perm in all_perms:
            role_perm = (
                self.db.query(RolePermission)
                .filter(RolePermission.role == "administrador", RolePermission.permission_id == perm.id)
                .first()
            )
            if not role_perm:
                self.db.add(RolePermission(role="administrador", permission_id=perm.id))

        # Default assignments for encargado_sucursal (sucursales.ver, productos.*)
        for perm in all_perms:
            if perm.module == "productos" or perm.code in ["sucursales.ver", "usuarios.ver"]:
                existing = (
                    self.db.query(RolePermission)
                    .filter(RolePermission.role == "encargado_sucursal", RolePermission.permission_id == perm.id)
                    .first()
                )
                if not existing:
                    self.db.add(RolePermission(role="encargado_sucursal", permission_id=perm.id))

        # Default assignments for cajero
        for perm in all_perms:
            if perm.code in ["productos.ver", "sucursales.ver", "categorias.ver", "colores.ver", "tallas.ver", "temporadas.ver", "clientes.ver"]:
                existing = (
                    self.db.query(RolePermission)
                    .filter(RolePermission.role == "cajero", RolePermission.permission_id == perm.id)
                    .first()
                )
                if not existing:
                    self.db.add(RolePermission(role="cajero", permission_id=perm.id))

        # Default assignments for cliente (ver catálogo y filtros de productos)
        for perm in all_perms:
            if perm.code in ["productos.ver", "sucursales.ver", "categorias.ver", "colores.ver", "tallas.ver", "temporadas.ver"]:
                existing = (
                    self.db.query(RolePermission)
                    .filter(RolePermission.role == "cliente", RolePermission.permission_id == perm.id)
                    .first()
                )
                if not existing:
                    self.db.add(RolePermission(role="cliente", permission_id=perm.id))

        self.db.commit()

    def list_roles(self) -> list[dict]:
        """List all system roles and their permission counts."""
        result = []
        for role in AVAILABLE_ROLES:
            count = self.db.query(RolePermission).filter(RolePermission.role == role).count()
            result.append({"role": role, "permission_count": count})
        return result

    def list_all_permissions(self) -> list[Permission]:
        """List all available permissions in the system."""
        return self.db.query(Permission).order_by(Permission.module, Permission.code).all()

    def get_role_permissions(self, role: str) -> dict:
        """Get all permissions assigned to a specific role."""
        if role not in AVAILABLE_ROLES:
            raise NotFoundException(f"El rol '{role}' no existe.")

        role_perms = (
            self.db.query(Permission)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .filter(RolePermission.role == role)
            .order_by(Permission.module, Permission.code)
            .all()
        )
        return {
            "role": role,
            "permissions": role_perms,
        }

    def update_role_permissions(
        self,
        role: str,
        permission_codes: list[str],
        current_user: User,
    ) -> dict:
        """Update permissions assigned to a role."""
        if role not in AVAILABLE_ROLES:
            raise NotFoundException(f"El rol '{role}' no existe.")

        # Fetch matching permissions
        permissions = (
            self.db.query(Permission)
            .filter(Permission.code.in_(permission_codes))
            .all()
        ) if permission_codes else []

        # Remove existing permissions for this role
        self.db.query(RolePermission).filter(RolePermission.role == role).delete()

        # Add new permissions
        for perm in permissions:
            self.db.add(RolePermission(role=role, permission_id=perm.id))

        self.db.commit()

        # Log action to bitacora
        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Actualizó los permisos del rol '{role}' ({len(permissions)} permisos asignados)",
            module="roles",
        )

        return self.get_role_permissions(role)
