"""Pydantic schemas for User data validation and serialization."""

from pydantic import BaseModel, EmailStr, ConfigDict


class UserCreate(BaseModel):
    """Schema for user registration request payload."""
    username: str | None = None
    email: EmailStr
    password: str
    full_name: str | None = None


class UserOut(BaseModel):
    """Schema for public user profile output (excluding password)."""
    id: int
    username: str
    email: EmailStr
    full_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """Schema for JSON login request payload."""
    username: str
    password: str


class Token(BaseModel):
    """Schema for JWT access token response payload."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for internal decoded JWT token payload data."""
    username: str | None = None