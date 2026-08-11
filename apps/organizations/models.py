"""SQLAlchemy database models for Organization Workspaces and Invites."""

from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, DateTime, Integer, func
from apps.database import Base


class Organization(Base):
    """Organization workspace model table 'organizations'."""
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    key: Mapped[str] = mapped_column(String(10), unique=True, index=True) # e.g. "FAA"
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    counter: Mapped[int] = mapped_column(Integer, default=0) # Counter for ticket sequence e.g. FAA-1
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    invites = relationship("OrganizationInvite", back_populates="organization", cascade="all, delete-orphan")


class OrganizationMember(Base):
    """OrganizationMember database model table 'organization_members'."""
    __tablename__ = "organization_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(50), default="member") # owner, admin, member
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization", back_populates="members")
    user = relationship("User")


class OrganizationInvite(Base):
    """OrganizationInvite database model table 'organization_invitations'."""
    __tablename__ = "organization_invitations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(255), index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(50), default="member")
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(50), default="pending") # pending, accepted, declined
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization", back_populates="invites")
    sender = relationship("User")
