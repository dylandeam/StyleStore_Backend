"""
User endpoints: profile, user data.
"""
from fastapi import APIRouter, Depends

from app.models.user import User
from app.schemas.user import UserResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the authenticated user's profile data.",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return current_user
