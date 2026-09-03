"""
Authentication endpoints: register, login, logout, refresh.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest
from app.schemas.user import UserResponse
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Register a new user",
    description="Create a new user account with email, password, and name.",
)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    auth_service = AuthService(db)
    user = auth_service.register(request)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate with email and password. Returns JWT access and refresh tokens.",
)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login and receive JWT tokens."""
    auth_service = AuthService(db)
    return auth_service.login(request.email, request.password)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout",
    description="Revoke the current access token by adding it to the blacklist.",
)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Logout by blacklisting the current token."""
    auth_service = AuthService(db)
    auth_service.logout(credentials.credentials)
    return MessageResponse(message="Successfully logged out")


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Get a new access token using a valid refresh token.",
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """Refresh the access token using a refresh token."""
    auth_service = AuthService(db)
    return auth_service.refresh_access_token(request.refresh_token)
