"""SQLAlchemy database model for Task entity."""

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from apps.database import Base


class Task(Base):
    """Task database model table 'tasks' bound to a foreign key User."""
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # -- Model fields
    title: Mapped[str]
    description: Mapped[str | None]
    completed: Mapped[bool] = mapped_column(default=False)
