"""CRUD (Create, Read, Update, Delete) database operations for User model."""

from sqlalchemy.orm import Session
from sqlalchemy import select
from apps.users.models import User
from apps.users.schemas import UserCreate
from apps.security import hash_password


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Fetch a single User record by primary key ID.

    Args:
        db (Session): Database session.
        user_id (int): Primary key user ID.

    Returns:
        User | None: User model instance if found, None otherwise.
    """
    return db.scalars(select(User).where(User.id == user_id)).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    """Fetch a single User record by unique username.

    Args:
        db (Session): Database session.
        username (str): Target username.

    Returns:
        User | None: User model instance if found, None otherwise.
    """
    return db.scalars(select(User).where(User.username == username)).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Fetch a single User record by unique email address.

    Args:
        db (Session): Database session.
        email (str): Target email address.

    Returns:
        User | None: User model instance if found, None otherwise.
    """
    return db.scalars(select(User).where(User.email == email)).first()


def create_user(db: Session, user_data: UserCreate) -> User:
    """Create a new user with a hashed password in the database.

    Args:
        db (Session): Database session.
        user_data (UserCreate): Input user registration schema.

    Returns:
        User: Newly created and refreshed User model instance.
    """
    hashed_pwd = hash_password(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        password=hashed_pwd
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user