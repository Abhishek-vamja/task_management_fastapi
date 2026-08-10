from datetime import datetime
from enum import Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, Enum as SqlEnum, String, DateTime, func
from apps.database import Base


class TaskStatus(str, Enum):
    """
    Enumeration of all possible task statuses.

    This enum is used to restrict the status field of a task
    to a predefined set of valid values.
    """

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    
class TaskType(str, Enum):
    """
    Enumeration of all possible task statuses.

    This enum is used to restrict the status field of a task
    to a predefined set of valid values.
    """

    FEATURE = "feature"
    BUG = "bug"
    TASK = "task"

class Task(Base):
    """Task database model table 'tasks' bound to a foreign key User."""
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    board_id: Mapped[int | None] = mapped_column(ForeignKey("boards.id"), nullable=True)

    # -- Model fields
    title: Mapped[str]
    description: Mapped[str | None]
    completed: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(50), default="todo", nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=True)
    tag: Mapped[str | None] = mapped_column(String(50), nullable=True)
    type: Mapped[TaskType] = mapped_column(
        SqlEnum(TaskType),
        default=TaskType.TASK,
        nullable=True,
    )
    position: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())
    description_updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

