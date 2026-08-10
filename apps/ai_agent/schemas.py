"""Pydantic schemas for AI agent data validation and response serialization."""

from pydantic import BaseModel, ConfigDict


class AIChatCreate(BaseModel):
    """Schema for AI Chat creation request body."""
    question: str
    answer: str | None = None
    ai_answer : str | None = None
    task_id:int | None = None


class AIChatResponse(BaseModel):
    """Schema for AI Chat response serialization."""
    id: int
    user_id: int
    task_id: int | None
    question: str
    answer: str | None
    ai_answer : str | None
