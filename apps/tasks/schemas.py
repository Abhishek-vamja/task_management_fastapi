"""Pydantic schemas for Task data validation and response serialization."""

from pydantic import BaseModel, ConfigDict


from datetime import datetime

class TaskCreate(BaseModel):
    """Schema for task creation request body."""
    title: str
    description: str | None = None
    completed: bool = False
    status: str = "todo"
    priority: str = "medium"
    tag: str | None = None
    assignee_id: int | None = None
    board_id: int | None = None
    position: int = 0


class TaskOut(BaseModel):
    """Schema for task response output."""
    id: int
    user_id: int
    title: str
    description: str | None
    completed: bool
    status: str
    priority: str
    tag: str | None
    assignee_id: int | None
    board_id: int | None
    position: int
    created_at: datetime
    description_updated_by: str | None = None
    description_updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskUpdate(BaseModel):
    """Schema for task update request body."""
    title: str | None = None
    description: str | None = None
    completed: bool | None = None
    status: str | None = None
    priority: str | None = None
    tag: str | None = None
    assignee_id: int | None = None
    board_id: int | None = None
    position: int | None = None
    description_updated_by: str | None = None
    description_updated_at: datetime | None = None


class FlowAI(BaseModel):
    """Schema for FlowAI response output."""

    question : str
    is_static : bool


class FlowAIOut(BaseModel):
    """Schema for FlowAI response output."""

    question: str
    is_static: bool = False
    answer: str | None = None
    
    model_config = ConfigDict(from_attributes=True)
