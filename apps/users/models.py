"""SQLAlchemy database model for User entity."""

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from apps.database import Base


class User(Base):
    """User database model table 'users'."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))
