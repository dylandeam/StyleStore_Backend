"""
Role and Permission Service (RBAC).
Conforme a Especificación StyleStore v5 (Sección 3).
"""
from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user import User
from app.core.exceptions import NotFoundException, BadRequestException
from app.services.bitacora_service import BitacoraService

AVAILABLE_ROLES = ["administrador", "encargado_sucursal", "cajero", "cliente"]

BASE_PERMISSIONS = [
    # Usuarios (CU1)
    {"code": "usuarios.crear", "module": "usuarios", "description": "Crear y registrar empleados o usuarios"},
    {"code": "usuarios.ver", "module": "usuarios", "description": "Visualizar listado y detalle de usuarios"},
    {"code": "usuarios.editar", "module": "usuarios", "description": "Editar información de usuarios"},
    {"code": "usuarios.eliminar", "module": "usuarios", "description": "Eliminar o desactivar usuarios"},

    # Roles y Permisos (CU5 / v5)
    {"code": "roles.crear", "module": "roles", "description": "Crear nuevos roles de usuario"},
    {"code": "roles.editar", "module": "roles", "description": "Editar roles existentes"},
    {"code": "roles.eliminar", "module": "roles", "description": "Eliminar roles que no tengan usuarios asociados"},
    {"code": "roles.ver", "module": "roles", "description": "Visualizar roles del sistema"},
    {"code": "roles.gestionar", "module": "roles", "description": "Gestionar asignación de permisos por rol"},

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

    # Colecciones (CU15 / v5)
    {"code": "colecciones.crear", "module": "colecciones", "description": "Crear nuevas colecciones"},
    {"code": "colecciones.editar", "module": "colecciones", "description": "Editar colecciones de moda"},
    {"code": "colecciones.eliminar", "module": "colecciones", "description": "Eliminar colecciones no asociadas a productos"},
    {"code": "colecciones.ver", "module": "colecciones", "description": "Visualizar colecciones"},

    # Productos (CU10 / CU17)
    {"code": "productos.crear", "module": "productos", "description": "Crear nuevos productos en catálogo"},
    {"code": "productos.editar", "module": "productos", "description": "Editar información y visibilidad de productos"},
    {"code": "productos.eliminar", "module": "productos", "description": "Eliminar o desactivar productos"},
    {"code": "productos.ver", "module": "productos", "description": "Visualizar gestión de productos"},

    # Catálogo (v5 sección 15)
    {"code": "catalogo.ver", "module": "catalogo", "description": "Visualizar catálogo público de productos"},

    # Próximamente (v5 sección 11)
    {"code": "proximamente.crear", "module": "proximamente", "description": "Registrar prendas de próximo lanzamiento"},
    {"code": "proximamente.editar", "module": "proximamente", "description": "Editar prendas próximas"},
    {"code": "proximamente.eliminar", "module": "proximamente", "description": "Eliminar prendas próximas"},
    {"code": "proximamente.ver", "module": "proximamente", "description": "Visualizar prendas próximas"},

    # Proveedores (CU16 / v5)
    {"code": "proveedores.crear", "module": "proveedores", "description": "Registrar nuevos proveedores"},
    {"code": "proveedores.editar", "module": "proveedores", "description": "Editar información de proveedores"},
    {"code": "proveedores.eliminar", "module": "proveedores", "description": "Eliminar proveedores"},
    {"code": "proveedores.ver", "module": "proveedores", "description": "Visualizar proveedores"},

    # Reservas (v5 sección 16)
    {"code": "reservas.crear", "module": "reservas", "description": "Crear reservas de prendas"},
    {"code": "reservas.ver", "module": "reservas", "description": "Visualizar reservas administrativas"},
    {"code": "reservas.editar", "module": "reservas", "description": "Actualizar estado de reservas"},
    {"code": "reservas.eliminar", "module": "reservas", "description": "Eliminar o cancelar reservas"},

    # Carrito y Ventas (v5 sección 17, 18, 23)
    {"code": "carrito.ver", "module": "carrito", "description": "Visualizar carritos de compra"},
    {"code": "ventas.ver", "module": "ventas", "description": "Visualizar listado consolidado de ventas"},
    {"code": "ventas.eliminar", "module": "ventas", "description": "Eliminar registros de venta"},

    # Envíos (v5 sección 24)
    {"code": "envios.ver", "module": "envios", "description": "Visualizar envíos de compras en línea"},
    {"code": "envios.editar", "module": "envios", "description": "Actualizar estado o información de envíos"},
    {"code": "envios.eliminar", "module": "envios", "description": "Eliminar registros de envíos"},

    # Inventario (v5 sección 25)
    {"code": "inventario.ver", "module": "inventario", "description": "Visualizar inventario global y por sucursal"},
    {"code": "inventario.editar", "module": "inventario", "description": "Ajustar o registrar stock de inventario"},

    # Auditoria
    {"code": "bitacora.ver", "module": "bitacora", "description": "Visualizar historial de auditoría y bitácora"},
]


class RoleService:
    """Service for managing RBAC roles and permissions."""

    def __init__(self, db: Session):
        self.db = db

    def seed_default_permissions_and_roles(self):
        """Seed base permissions and assign default roles dynamically."""
        # 1. Ensure all base permissions exist
        for perm_data in BASE_PERMISSIONS:
            existing = self.db.query(Permission).filter(Permission.code == perm_data["code"]).first()
            if not existing:
                perm = Permission(
                    code=perm_data["code"],
                    module=perm_data["module"],
                    description=perm_data["description"],
                )
                self.db.add(perm)
            else:
                existing.description = perm_data["description"]
                existing.module = perm_data["module"]
        self.db.commit()

        # 2. Ensure base roles exist in `roles` table
        base_role_defs = [
            ("Administrador", "Acceso total y administración de la plataforma StyleStore"),
            ("Encargado de Sucursal", "Gestión de catálogo, sucursales, reservas e inventario"),
            ("Cajero", "Atención en punto de venta, compras presenciales y facturación"),
            ("Cliente", "Usuario comprador con acceso a catálogo, carrito, reservas y compras"),
        ]

        role_map: dict[str, Role] = {}
        for role_name, desc in base_role_defs:
            role_obj = self.db.query(Role).filter(Role.nombre.ilike(role_name)).first()
            if not role_obj:
                role_obj = Role(nombre=role_name, descripcion=desc, active=True)
                self.db.add(role_obj)
                self.db.flush()
            role_map[role_name.lower()] = role_obj

        self.db.commit()

        # 3. Backfill users role_id
        admin_role = role_map.get("administrador")
        cliente_role = role_map.get("cliente")
        cajero_role = role_map.get("cajero")
        encargado_role = role_map.get("encargado de sucursal")

        users_without_role_id = self.db.query(User).filter(User.role_id.is_(None)).all()
        for u in users_without_role_id:
            r_str = (u.role or "cliente").lower()
            if "admin" in r_str and admin_role:
                u.role_id = admin_role.id
            elif "encargado" in r_str and encargado_role:
                u.role_id = encargado_role.id
            elif "cajero" in r_str and cajero_role:
                u.role_id = cajero_role.id
            elif cliente_role:
                u.role_id = cliente_role.id
        self.db.commit()

        # 4. Assign permissions to roles
        all_perms = self.db.query(Permission).all()

        # Administrador gets all permissions
        if admin_role:
            for perm in all_perms:
                exists = (
                    self.db.query(RolePermission)
                    .filter((RolePermission.role_id == admin_role.id) | (RolePermission.role == "administrador"))
                    .filter(RolePermission.permission_id == perm.id)
                    .first()
                )
                if not exists:
                    self.db.add(RolePermission(role_id=admin_role.id, role="administrador", permission_id=perm.id))

        # Encargado de Sucursal
        if encargado_role:
            for perm in all_perms:
                if perm.module in ["productos", "categorias", "colores", "tallas", "temporadas", "colecciones", "proximamente", "reservas", "inventario", "catalogo"] or perm.code in ["sucursales.ver", "usuarios.ver"]:
                    exists = (
                        self.db.query(RolePermission)
                        .filter((RolePermission.role_id == encargado_role.id) | (RolePermission.role == "encargado_sucursal"))
                        .filter(RolePermission.permission_id == perm.id)
                        .first()
                    )
                    if not exists:
                        self.db.add(RolePermission(role_id=encargado_role.id, role="encargado_sucursal", permission_id=perm.id))

        # Cajero
        if cajero_role:
            for perm in all_perms:
                if perm.code in [
                    "productos.ver", "catalogo.ver", "sucursales.ver", "categorias.ver",
                    "colores.ver", "tallas.ver", "temporadas.ver", "colecciones.ver",
                    "clientes.ver", "ventas.ver", "reservas.ver", "inventario.ver"
                ]:
                    exists = (
                        self.db.query(RolePermission)
                        .filter((RolePermission.role_id == cajero_role.id) | (RolePermission.role == "cajero"))
                        .filter(RolePermission.permission_id == perm.id)
                        .first()
                    )
                    if not exists:
                        self.db.add(RolePermission(role_id=cajero_role.id, role="cajero", permission_id=perm.id))

        # Cliente
        if cliente_role:
            for perm in all_perms:
                if perm.code in [
                    "catalogo.ver", "productos.ver", "sucursales.ver",
                    "categorias.ver", "colores.ver", "tallas.ver", "temporadas.ver",
                    "colecciones.ver", "proximamente.ver", "reservas.crear"
                ]:
                    exists = (
                        self.db.query(RolePermission)
                        .filter((RolePermission.role_id == cliente_role.id) | (RolePermission.role == "cliente"))
                        .filter(RolePermission.permission_id == perm.id)
                        .first()
                    )
                    if not exists:
                        self.db.add(RolePermission(role_id=cliente_role.id, role="cliente", permission_id=perm.id))

        self.db.commit()

    def list_roles(self) -> list[dict]:
        """List all system roles and their permission counts."""
        roles = self.db.query(Role).order_by(Role.id).all()
        result = []
        for r in roles:
            perm_count = (
                self.db.query(RolePermission)
                .filter((RolePermission.role_id == r.id) | (RolePermission.role == r.nombre.lower()))
                .count()
            )
            user_count = self.db.query(User).filter(User.role_id == r.id).count()
            result.append({
                "id": r.id,
                "nombre": r.nombre,
                "descripcion": r.descripcion,
                "active": r.active,
                "role": r.nombre.lower().replace(" ", "_"),
                "permission_count": perm_count,
                "user_count": user_count,
                "created_at": r.created_at,
            })
        return result

    def get_role_by_id(self, role_id: int) -> Role:
        """Get role by ID or raise 404."""
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise NotFoundException(f"El rol con ID {role_id} no existe.")
        return role

    def create_role(self, nombre: str, descripcion: str | None, current_user: User) -> Role:
        """Create a new role."""
        existing = self.db.query(Role).filter(Role.nombre.ilike(nombre.strip())).first()
        if existing:
            raise BadRequestException(f"Ya existe un rol con el nombre '{nombre}'.")

        role = Role(
            nombre=nombre.strip(),
            descripcion=descripcion.strip() if descripcion else None,
            active=True,
        )
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)

        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Creó el rol '{role.nombre}' (ID: {role.id})",
            module="roles",
        )
        return role

    def update_role(self, role_id: int, nombre: str | None, descripcion: str | None, active: bool | None, current_user: User) -> Role:
        """Update role information."""
        role = self.get_role_by_id(role_id)
        if nombre and nombre.strip() != role.nombre:
            existing = self.db.query(Role).filter(Role.nombre.ilike(nombre.strip()), Role.id != role_id).first()
            if existing:
                raise BadRequestException(f"Ya existe otro rol con el nombre '{nombre}'.")
            role.nombre = nombre.strip()

        if descripcion is not None:
            role.descripcion = descripcion.strip() if descripcion else None

        if active is not None:
            role.active = active

        self.db.commit()
        self.db.refresh(role)

        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Actualizó el rol '{role.nombre}' (ID: {role.id})",
            module="roles",
        )
        return role

    def delete_role(self, role_id: int, current_user: User) -> dict:
        """Delete a role if it has no assigned users."""
        role = self.get_role_by_id(role_id)

        # Critical v5 rule: do not delete if it has users
        assigned_users = self.db.query(User).filter(User.role_id == role.id).count()
        if assigned_users > 0:
            raise BadRequestException(f"No se puede eliminar el rol '{role.nombre}' porque tiene {assigned_users} usuario(s) asignado(s).")

        # Do not delete system base admin role
        if role.nombre.lower() == "administrador":
            raise BadRequestException("El rol Administrador es fundamental para el sistema y no se puede eliminar.")

        # Delete associated role permissions
        self.db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()
        self.db.delete(role)
        self.db.commit()

        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Eliminó el rol '{role.nombre}' (ID: {role_id})",
            module="roles",
        )
        return {"message": f"Rol '{role.nombre}' eliminado exitosamente."}

    def list_all_permissions(self) -> list[Permission]:
        """List all available permissions in the system."""
        return self.db.query(Permission).order_by(Permission.module, Permission.code).all()

    def get_role_permissions(self, role_id_or_name: str | int) -> dict:
        """Get all permissions assigned to a specific role."""
        if isinstance(role_id_or_name, int) or (isinstance(role_id_or_name, str) and role_id_or_name.isdigit()):
            role = self.get_role_by_id(int(role_id_or_name))
        else:
            role = self.db.query(Role).filter(Role.nombre.ilike(str(role_id_or_name).replace("_", " "))).first()
            if not role:
                role = self.db.query(Role).filter(Role.nombre.ilike(str(role_id_or_name))).first()
            if not role:
                raise NotFoundException(f"El rol '{role_id_or_name}' no existe.")

        role_perms = (
            self.db.query(Permission)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .filter((RolePermission.role_id == role.id) | (RolePermission.role == role.nombre.lower()))
            .order_by(Permission.module, Permission.code)
            .all()
        )
        return {
            "id": role.id,
            "nombre": role.nombre,
            "role": role.nombre.lower().replace(" ", "_"),
            "permissions": role_perms,
        }

    def update_role_permissions(
        self,
        role_id_or_name: str | int,
        permission_codes: list[str],
        current_user: User,
    ) -> dict:
        """Update permissions assigned to a role."""
        if isinstance(role_id_or_name, int) or (isinstance(role_id_or_name, str) and role_id_or_name.isdigit()):
            role = self.get_role_by_id(int(role_id_or_name))
        else:
            role = self.db.query(Role).filter(Role.nombre.ilike(str(role_id_or_name).replace("_", " "))).first()
            if not role:
                role = self.db.query(Role).filter(Role.nombre.ilike(str(role_id_or_name))).first()
            if not role:
                raise NotFoundException(f"El rol '{role_id_or_name}' no existe.")

        # Fetch matching permissions
        permissions = (
            self.db.query(Permission)
            .filter(Permission.code.in_(permission_codes))
            .all()
        ) if permission_codes else []

        # Remove existing permissions for this role
        self.db.query(RolePermission).filter(
            (RolePermission.role_id == role.id) | (RolePermission.role == role.nombre.lower())
        ).delete()

        # Add new permissions
        for perm in permissions:
            self.db.add(RolePermission(role_id=role.id, role=role.nombre.lower(), permission_id=perm.id))

        self.db.commit()

        # Log action to bitacora
        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Actualizó los permisos del rol '{role.nombre}' ({len(permissions)} permisos asignados)",
            module="roles",
        )

        return self.get_role_permissions(role.id)
