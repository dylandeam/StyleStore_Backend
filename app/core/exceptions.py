"""
Custom exception classes for the application.
"""
from fastapi import HTTPException, status


class CredentialsException(HTTPException):
    """Raised when authentication credentials are invalid."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class UserAlreadyExistsException(HTTPException):
    """Raised when trying to register with an existing email."""

    def __init__(self, detail: str = "A user with this email already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class UserNotFoundException(HTTPException):
    """Raised when a user is not found."""

    def __init__(self, detail: str = "User not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class InvalidTokenException(HTTPException):
    """Raised when a token is invalid or blacklisted."""

    def __init__(self, detail: str = "Token is invalid or has been revoked"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(HTTPException):
    """Raised when the user does not have permission to perform an action."""

    def __init__(self, detail: str = "No tiene permisos para realizar esta acción"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class InvalidOrExpiredTokenException(HTTPException):
    """Raised when a password reset or confirmation token is invalid or expired."""

    def __init__(self, detail: str = "El enlace de confirmación no es válido o ha expirado"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class NotFoundException(HTTPException):
    """Generic 404 exception for entities."""

    def __init__(self, detail: str = "Recurso no encontrado"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class ConflictException(HTTPException):
    """Generic 409 exception for entity conflicts."""

    def __init__(self, detail: str = "El recurso ya existe o genera conflicto"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )

