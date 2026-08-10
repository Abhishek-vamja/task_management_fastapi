from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict
from apps.users.schemas import UserOut


class BoardCreate(BaseModel):
    """Schema for board creation request payload."""
    name: str
    description: str | None = None
    type: str = "team"
    privacy: str = "private"
    accent_color: str = "blue"
    icon: str = "folder"
    columns: list[str] = ["todo", "in_progress", "in_review", "done"]


class BoardOut(BaseModel):
    """Schema for board details output."""
    id: int
    name: str
    description: str | None
    owner_id: int
    type: str
    privacy: str
    accent_color: str
    icon: str
    columns: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BoardMemberOut(BaseModel):
    """Schema for board member information."""
    id: int
    board_id: int
    user_id: int
    role: str
    user: UserOut

    model_config = ConfigDict(from_attributes=True)


class InvitationCreate(BaseModel):
    """Schema for inviting a new member to a board."""
    email: EmailStr
    role: str = "developer"
    personal_message: str | None = None


class InvitationOut(BaseModel):
    """Schema for board invitation details output."""
    id: int
    email: str
    board_id: int
    role: str
    personal_message: str | None
    token: str
    status: str
    sender_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskReorderItem(BaseModel):
    """Schema for individual task reorder details."""
    id: int
    position: int
    status: str


class TasksReorderRequest(BaseModel):
    """Schema for bulk task reorder request payload."""
    tasks: list[TaskReorderItem]
