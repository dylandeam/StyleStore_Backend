"""
User service — business logic for user-related operations and employee management.
"""
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreateByAdmin, UserUpdateByAdmin
from app.core.security import hash_password
from app.core.exceptions import UserNotFoundException, UserAlreadyExistsException
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
            query = query.filter(User.role == role)
        if search:
            query = query.filter(
                (User.name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
            )
        return query.order_by(User.created_at.desc()).all()

    def create_employee(self, request: UserCreateByAdmin, current_user: User) -> User:
        """
        Create an employee account with assigned role (CU1).
        """
        existing = self.get_user_by_email(request.email)
        if existing:
            raise UserAlreadyExistsException("Ya existe un usuario con este correo electrónico.")

        user = User(
            email=request.email,
            name=request.name,
            hashed_password=hash_password(request.password),
            role=request.role,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Log employee creation in bitacora
        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Registró empleado '{user.name}' ({user.email}) con rol '{user.role}'",
            module="usuarios",
        )

        return user

    def update_user_by_admin(
        self, user_id: int, request: UserUpdateByAdmin, current_user: User
    ) -> User:
        """Update user properties (role, active status, name) by administrator."""
        user = self.get_user_by_id(user_id)

        if request.name is not None:
            user.name = request.name
        if request.role is not None:
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
