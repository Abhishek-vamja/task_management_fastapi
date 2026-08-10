"""SQLAlchemy database model for AI Agenet entity."""
from enum import Enum

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, Enum as SqlEnum
from apps.database import Base


class AIChat(Base):
    """AI Agent database model table 'ai_chats' bound to a foreign key User."""
    __tablename__ = "ai_chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # -- Model fields
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    question: Mapped[str]
    answer: Mapped[str | None]
    ai_answer: Mapped[str | None]
