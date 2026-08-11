"""SQLAlchemy database model for AI Agent entity."""
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, DateTime, String
from apps.database import Base


class AIChatSession(Base):
    """AI Chat session thread table 'ai_chat_sessions'."""
    __tablename__ = "ai_chat_sessions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255), default="New Chat")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    chats = relationship("AIChat", back_populates="session", cascade="all, delete-orphan")


class AIChat(Base):
    """AI Agent database model table 'ai_chats' bound to a foreign key User and optional AIChatSession."""
    __tablename__ = "ai_chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[str | None] = mapped_column(ForeignKey("ai_chat_sessions.id", ondelete="CASCADE"), nullable=True)

    # -- Model fields
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    question: Mapped[str]
    answer: Mapped[str | None]
    ai_answer: Mapped[str | None]

    session = relationship("AIChatSession", back_populates="chats")
