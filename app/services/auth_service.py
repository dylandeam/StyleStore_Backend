"""
Authentication service — business logic for register, login, logout.
"""
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.token_blacklist import TokenBlacklist
from app.schemas.auth import RegisterRequest, TokenResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.exceptions import (
    CredentialsException,
    UserAlreadyExistsException,
    InvalidTokenException,
)


from app.services.bitacora_service import BitacoraService


class AuthService:
    """Handles authentication business logic."""

    def __init__(self, db: Session):
        self.db = db

    def register(self, request: RegisterRequest) -> User:
        """
        Register a new client user.
        """
        # Check if user already exists
        existing_user = (
            self.db.query(User).filter(User.email == request.email).first()
        )
        if existing_user:
            raise UserAlreadyExistsException("Ya existe un usuario registrado con este correo electrónico.")

        # Create new user with default client role
        user = User(
            email=request.email,
            name=request.name,
            hashed_password=hash_password(request.password),
            role="cliente",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Log registration in bitacora
        BitacoraService.registrar(
            db=self.db,
            user=user,
            action="Registró un nuevo usuario",
            module="auth",
        )

        return user

    def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate a user and return JWT tokens.
        """
        # Find user by email
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            BitacoraService.registrar(
                db=self.db,
                user=email,
                action="Intento fallido de inicio de sesión (correo no registrado)",
                module="auth",
            )
            raise CredentialsException(detail="Correo o contraseña incorrectos")

        # Verify password
        if not verify_password(password, user.hashed_password):
            BitacoraService.registrar(
                db=self.db,
                user=user,
                action="Intento fallido de inicio de sesión (contraseña incorrecta)",
                module="auth",
            )
            raise CredentialsException(detail="Correo o contraseña incorrectos")

        # Check if user is active
        if not user.is_active:
            raise CredentialsException(detail="La cuenta de usuario está desactivada")

        # Generate tokens
        token_data = {"sub": str(user.id), "role": user.role, "email": user.email}
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        # Log successful login in bitacora
        BitacoraService.registrar(
            db=self.db,
            user=user,
            action="Inició sesión",
            module="auth",
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    def logout(self, token: str, current_user: User | None = None) -> None:
        """
        Revoke a token by adding it to the blacklist.
        """
        # Check if token is already blacklisted
        existing = (
            self.db.query(TokenBlacklist)
            .filter(TokenBlacklist.token == token)
            .first()
        )
        if not existing:
            blacklisted = TokenBlacklist(token=token)
            self.db.add(blacklisted)
            self.db.commit()

        if current_user:
            BitacoraService.registrar(
                db=self.db,
                user=current_user,
                action="Cerró sesión",
                module="auth",
            )

    def is_token_blacklisted(self, token: str) -> bool:
        """Check if a token has been revoked."""
        return (
            self.db.query(TokenBlacklist)
            .filter(TokenBlacklist.token == token)
            .first()
            is not None
        )

    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Generate a new access token using a valid refresh token.
        
        Args:
            refresh_token: A valid refresh token.
        
        Returns:
            New TokenResponse with fresh access token.
        
        Raises:
            InvalidTokenException: If refresh token is invalid or blacklisted.
        """
        # Check if token is blacklisted
        if self.is_token_blacklisted(refresh_token):
            raise InvalidTokenException()

        # Decode the refresh token
        payload = decode_token(refresh_token)
        if payload is None:
            raise InvalidTokenException()

        if payload.get("type") != "refresh":
            raise InvalidTokenException(detail="Invalid token type")

        user_id = payload.get("sub")
        if user_id is None:
            raise InvalidTokenException()

        # Generate new access token
        token_data = {"sub": user_id}
        new_access_token = create_access_token(data=token_data)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
