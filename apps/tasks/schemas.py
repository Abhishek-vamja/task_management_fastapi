"""Pydantic schemas for Task data validation and response serialization."""

from pydantic import BaseModel, ConfigDict


class TaskCreate(BaseModel):
    """Schema for task creation request body."""
    title: str
    description: str | None = None
    completed: bool = False


class TaskOut(BaseModel):
    """Schema for task response output."""
    id: int
    user_id: int
    title: str
    description: str | None
    completed: bool

    model_config = ConfigDict(from_attributes=True)
