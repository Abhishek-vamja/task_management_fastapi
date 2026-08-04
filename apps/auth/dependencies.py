"""Security dependencies for authenticating requests using JWT Bearer tokens."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from apps.database import get_db
from apps.security import decode_access_token
from apps.users.crud import get_user_by_username
from apps.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI dependency to extract and validate the JWT token from request headers.

    Args:
        token (str): JWT token string extracted by OAuth2PasswordBearer.
        db (Session): Database session dependency.

    Raises:
        HTTPException: HTTP 401 Unauthorized if token is missing, invalid, expired, or user not found.

    Returns:
        User: Authenticated SQLAlchemy User model instance.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str | None = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception

    return user
