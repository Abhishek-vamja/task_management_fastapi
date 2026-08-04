"""Database setup module for SQLAlchemy ORM sessions and Base declarative models."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

from apps.config import DATABASE_URL


engine = create_engine(
    DATABASE_URL,
    echo=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy database models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency generator that yields a SQLAlchemy database session.

    Yields:
        Session: Active database session.
    """
    db = SessionLocal()
    print("Getting database session")
    try:
        yield db
    finally:
        db.close()
        print("Closing database session")
