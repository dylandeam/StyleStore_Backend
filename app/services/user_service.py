"""
User service — business logic for user-related operations, personal profile and employee management.
Conforme a Especificación StyleStore v5.
"""
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreateByAdmin, UserUpdateByAdmin, UserProfileUpdateRequest
from app.core.security import hash_password
from app.core.exceptions import UserNotFoundException, UserAlreadyExistsException, BadRequestException
from app.services.bitacora_service import BitacoraService


class UserService:
    """Handles user-related business logic."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int) -> User:
        """Get a user by their ID."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundException("Usuario no encontrado")
        return user

    def get_user_by_email(self, email: str) -> User | None:
        """Get a user by their email address."""
        return self.db.query(User).filter(User.email == email).first()

    def list_users(
        self,
        search: str | None = None,
        role: str | None = None,
    ) -> list[User]:
        """List users with optional search and role filtering."""
        query = self.db.query(User)
        if role:
            if role.isdigit():
                query = query.filter(User.role_id == int(role))
            else:
                query = query.filter(
                    (User.role.ilike(role)) | (User.role.ilike(f"%{role}%"))
                )
        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                (User.name.ilike(search_term))
                | (User.apellido.ilike(search_term))
                | (User.email.ilike(search_term))
                | (User.ci.ilike(search_term))
            )
        return query.order_by(User.created_at.desc()).all()

    def update_profile(self, user_id: int, request: UserProfileUpdateRequest) -> User:
        """Update personal profile information (CU2 / v5 Sección 2).
        CI is NOT modified to preserve identifier integrity.
        """
        user = self.get_user_by_id(user_id)

        if request.email and request.email != user.email:
            existing = self.get_user_by_email(request.email)
            if existing and existing.id != user.id:
                raise UserAlreadyExistsException("Ya existe otro usuario con este correo electrónico.")
            user.email = request.email

        if request.name is not None:
            user.name = request.name.strip()
        if request.apellido is not None:
            user.apellido = request.apellido.strip()
        if request.telefono is not None:
            user.telefono = request.telefono.strip()
        if request.direccion is not None:
            user.direccion = request.direccion.strip()
        if request.foto is not None:
            user.foto = request.foto.strip()

        self.db.commit()
        self.db.refresh(user)

        BitacoraService.registrar(
            db=self.db,
            user=user,
            action=f"Actualizó su información personal de perfil",
            module="usuarios",
        )
        return user

    def create_employee(self, request: UserCreateByAdmin, current_user: User) -> User:
        """Create a user/employee account with assigned role (CU1 / v5 Sección 4).
        Default password is CI if not explicitly specified.
        """
        existing = self.get_user_by_email(request.email)
        if existing:
            raise UserAlreadyExistsException("Ya existe un usuario con este correo electrónico.")

        if request.ci:
            existing_ci = self.db.query(User).filter(User.ci == request.ci.strip()).first()
            if existing_ci:
                raise BadRequestException(f"Ya existe un usuario con el CI '{request.ci}'.")

        # Resolve role
        role_obj = None
        if request.role_id:
            role_obj = self.db.query(Role).filter(Role.id == request.role_id).first()
        if not role_obj and request.role:
            role_obj = (
                self.db.query(Role)
                .filter((Role.nombre.ilike(request.role.replace("_", " "))) | (Role.nombre.ilike(request.role)))
                .first()
            )

        role_str = role_obj.nombre.lower().replace(" ", "_") if role_obj else request.role.lower()
        role_id_val = role_obj.id if role_obj else None

        # v5 Rule: Default password equals CI
        ci_str = request.ci.strip() if request.ci else "12345678"
        raw_password = request.password.strip() if (request.password and request.password.strip()) else ci_str

        raw_name = request.name.strip() if request.name else ""
        raw_apellido = request.apellido.strip() if request.apellido else ""
        if raw_apellido and raw_name.lower().endswith(raw_apellido.lower()) and len(raw_name) > len(raw_apellido):
            clean_name = raw_name[:-len(raw_apellido)].strip()
            clean_apellido = raw_apellido
        elif not raw_apellido:
            clean_name = raw_name
            clean_apellido = None
        else:
            clean_name = raw_name
            clean_apellido = raw_apellido

        user = User(
            email=request.email,
            name=clean_name,
            apellido=clean_apellido,
            ci=request.ci.strip() if request.ci else None,
            hashed_password=hash_password(raw_password),
            role=role_str,
            role_id=role_id_val,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Log employee creation in bitacora
        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Registró usuario/empleado '{user.name}' ({user.email}) con rol '{user.role}'",
            module="usuarios",
        )

        return user

    def update_user_by_admin(
        self, user_id: int, request: UserUpdateByAdmin, current_user: User
    ) -> User:
        """Update user properties (role, active status, name) by administrator."""
        user = self.get_user_by_id(user_id)

        if request.name is not None:
            user.name = request.name.strip()
        if request.apellido is not None:
            user.apellido = request.apellido.strip()
        if request.ci is not None:
            user.ci = request.ci.strip()
        if request.telefono is not None:
            user.telefono = request.telefono.strip()
        if request.direccion is not None:
            user.direccion = request.direccion.strip()

        if request.role_id is not None:
            role_obj = self.db.query(Role).filter(Role.id == request.role_id).first()
            if role_obj:
                user.role_id = role_obj.id
                user.role = role_obj.nombre.lower().replace(" ", "_")
        elif request.role is not None:
            role_obj = (
                self.db.query(Role)
                .filter((Role.nombre.ilike(request.role.replace("_", " "))) | (Role.nombre.ilike(request.role)))
                .first()
            )
            if role_obj:
                user.role_id = role_obj.id
                user.role = role_obj.nombre.lower().replace(" ", "_")
            else:
                user.role = request.role

        if request.is_active is not None:
            user.is_active = request.is_active

        self.db.commit()
        self.db.refresh(user)

        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Actualizó datos del usuario '{user.email}' (Rol: {user.role}, Activo: {user.is_active})",
            module="usuarios",
        )
        return user
