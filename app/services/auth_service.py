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


class AuthService:
    """Handles authentication business logic."""

    def __init__(self, db: Session):
        self.db = db

    def register(self, request: RegisterRequest) -> User:
        """
        Register a new user.
        
        Args:
            request: Registration data with email, password, name.
        
        Returns:
            The created User object.
        
        Raises:
            UserAlreadyExistsException: If email is already registered.
        """
        # Check if user already exists
        existing_user = (
            self.db.query(User).filter(User.email == request.email).first()
        )
        if existing_user:
            raise UserAlreadyExistsException()

        # Create new user
        user = User(
            email=request.email,
            name=request.name,
            hashed_password=hash_password(request.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate a user and return JWT tokens.
        
        Args:
            email: User email.
            password: Plain-text password.
        
        Returns:
            TokenResponse with access and refresh tokens.
        
        Raises:
            CredentialsException: If email/password is invalid.
        """
        # Find user by email
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise CredentialsException(detail="Invalid email or password")

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise CredentialsException(detail="Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise CredentialsException(detail="User account is deactivated")

        # Generate tokens
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    def logout(self, token: str) -> None:
        """
        Revoke a token by adding it to the blacklist.
        
        Args:
            token: The JWT token to blacklist.
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
