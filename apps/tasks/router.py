"""API router for Task domain endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from apps.database import get_db
from apps.pagination import PaginatedResponse
from apps.tasks import crud
from apps.tasks.schemas import TaskCreate, TaskOut
from apps.auth.dependencies import get_current_user
from apps.users.models import User

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new private task bound to the authenticated user.

    Args:
        task_in (TaskCreate): Input task creation payload.
        db (Session): Database session dependency.
        current_user (User): Authenticated user dependency.

    Returns:
        TaskOut: Created task response object.
    """
    task = crud.create_task(db, task_data=task_in, user_id=current_user.id)
    return task


@router.get("/", response_model=PaginatedResponse[TaskOut])
def read_user_tasks(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(default=10, ge=1, le=100, description="Number of items per page (max 100)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a paginated list of tasks belonging to the authenticated user.

    Args:
        page (int, optional): Page index starting at 1. Defaults to 1.
        limit (int, optional): Page item limit (max 100). Defaults to 10.
        db (Session): Database session dependency.
        current_user (User): Authenticated user dependency.

    Returns:
        PaginatedResponse[TaskOut]: Paginated envelope containing task list and metadata.
    """
    return crud.get_user_tasks_paginated(
        db,
        user_id=current_user.id,
        page=page,
        limit=limit
    )
