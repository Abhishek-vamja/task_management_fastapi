"""API router for User domain endpoints."""

from fastapi import APIRouter, Depends
from apps.users.schemas import UserOut
from apps.auth.dependencies import get_current_user
from apps.users.models import User

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get("/me", response_model=UserOut)
def get_user_me(current_user: User = Depends(get_current_user)):
    """Retrieve current authenticated user profile.

    Args:
        current_user (User): Authenticated user instance from JWT dependency.

    Returns:
        UserOut: Current user's details.
    """
    return current_user