"""SQLAlchemy database model for Task entity."""
from enum import Enum

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, Enum as SqlEnum
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

    # -- Model fields
    title: Mapped[str]
    description: Mapped[str | None]
    completed: Mapped[bool] = mapped_column(default=False)
    status: Mapped[TaskStatus] = mapped_column(
        SqlEnum(TaskStatus),
        default=TaskStatus.TODO,
        nullable=True,
    )
    type: Mapped[TaskType] = mapped_column(
        SqlEnum(TaskType),
        default=TaskType.TASK,
        nullable=True,
    )
