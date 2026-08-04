"""CRUD database operations for Task entity."""

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from apps.tasks.models import Task
from apps.tasks.schemas import TaskCreate


def get_task_by_id(db: Session, task_id: int) -> Task | None:
    """Fetch a single Task record by primary key ID.

    Args:
        db (Session): Database session.
        task_id (int): Primary key task ID.

    Returns:
        Task | None: Task model instance if found, None otherwise.
    """
    return db.scalars(select(Task).where(Task.id == task_id)).first()


def get_user_tasks_paginated(
    db: Session,
    user_id: int,
    page: int = 1,
    limit: int = 10
) -> dict:
    """Fetch a paginated list of tasks belonging to a specific user.

    Args:
        db (Session): Database session.
        user_id (int): Owner user ID.
        page (int, optional): Page number (1-indexed). Defaults to 1.
        limit (int, optional): Items per page. Defaults to 10.

    Returns:
        dict: Dictionary matching PaginatedResponse structure (items, total, page, limit, pages).
    """
    skip = (page - 1) * limit

    # Count total records for the user
    total_query = select(func.count()).select_from(Task).where(Task.user_id == user_id)
    total = db.scalar(total_query) or 0

    # Fetch paginated items
    items_query = (
        select(Task)
        .where(Task.user_id == user_id)
        .order_by(Task.id.desc())
        .offset(skip)
        .limit(limit)
    )
    items = list(db.scalars(items_query).all())

    # Calculate total pages
    pages = (total + limit - 1) // limit if total > 0 else 1

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages
    }


def create_task(db: Session, task_data: TaskCreate, user_id: int) -> Task:
    """Create a new Task assigned to a specific user ID.

    Args:
        db (Session): Database session.
        task_data (TaskCreate): Task creation input schema.
        user_id (int): Authenticated owner user ID.

    Returns:
        Task: Newly created and refreshed Task model instance.
    """
    db_task = Task(
        user_id=user_id,
        title=task_data.title,
        description=task_data.description,
        completed=task_data.completed
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task
