from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, String, DateTime, JSON, func
from apps.database import Base


class Board(Base):
    """Board database model table 'boards'."""
    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    type: Mapped[str] = mapped_column(String(50), default="team") # team, personal
    privacy: Mapped[str] = mapped_column(String(50), default="private") # private, public, org
    accent_color: Mapped[str] = mapped_column(String(50), default="blue")
    icon: Mapped[str] = mapped_column(String(50), default="folder")
    columns: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())


class BoardMember(Base):
    """BoardMember database model table 'board_members' mapping users to boards with specific roles."""
    __tablename__ = "board_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(50), default="developer") # manager, lead, designer, developer


class Invitation(Base):
    """Invitation database model table 'invitations' for tracking pending workspace/board invites."""
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(50), default="developer")
    personal_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending") # pending, accepted, declined
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())
