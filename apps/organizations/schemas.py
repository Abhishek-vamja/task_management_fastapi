"""Pydantic schemas for Organization request and response validation."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class OrganizationCreate(BaseModel):
    """Schema for creating a new Organization."""
    name: str
    key: str # e.g. "FAA"


class OrganizationOut(BaseModel):
    """Schema for Organization response."""
    id: int
    name: str
    key: str
    owner_id: int
    counter: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationMemberOut(BaseModel):
    """Schema for Organization member response."""
    id: int
    organization_id: int
    user_id: int
    role: str
    joined_at: datetime
    username: str | None = None
    email: str | None = None
    full_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationInviteCreate(BaseModel):
    """Schema for sending an Organization invite."""
    email: str
    role: str = "member"


class OrganizationInviteOut(BaseModel):
    """Schema for Organization invite output."""
    id: int
    organization_id: int
    email: str
    token: str
    role: str
    sender_id: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationMigrateSetup(BaseModel):
    """Schema for existing user initial Organization setup & data migration."""
    name: str
    key: str
