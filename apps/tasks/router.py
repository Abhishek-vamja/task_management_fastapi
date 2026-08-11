"""API router for Task domain endpoints."""

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from apps.database import get_db
from apps.pagination import PaginatedResponse
from apps.tasks import crud
from apps.tasks.schemas import TaskCreate, TaskOut, TaskUpdate
from apps.boards.schemas import TasksReorderRequest
from apps.auth.dependencies import get_current_user
from apps.users.models import User
from apps.ai_agent.models import AIChat

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


from fastapi import APIRouter, Depends, Query, Header, status, HTTPException

@router.get("/", response_model=PaginatedResponse[TaskOut])
def read_user_tasks(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(default=10, ge=1, le=100, description="Number of items per page (max 100)"),
    organization_id: int | None = Query(None),
    x_organization_id: int | None = Header(None, alias="X-Organization-Id"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a paginated list of tasks belonging to the authenticated user, filtered by organization_id."""
    target_org_id = organization_id or x_organization_id
    return crud.get_user_tasks_paginated(
        db,
        user_id=current_user.id,
        page=page,
        limit=limit,
        organization_id=target_org_id
    )


@router.get("/{task_id}", response_model=TaskOut)
def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch task details. Requires task owner or board membership."""
    task = crud.get_task_by_id(db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.user_id != current_user.id:
        if task.board_id:
            from apps.boards.crud import get_board_member
            member = get_board_member(db, board_id=task.board_id, user_id=current_user.id)
            if not member:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return task


@router.put("/reorder", status_code=status.HTTP_200_OK)
def reorder_tasks(
    reorder_in: TasksReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk update task positions and columns after drag-and-drop actions."""
    for item in reorder_in.tasks:
        task = crud.get_task_by_id(db, task_id=item.id)
        if task:
            # Check permissions
            if task.user_id != current_user.id:
                if task.board_id:
                    from apps.boards.crud import get_board_member
                    member = get_board_member(db, board_id=task.board_id, user_id=current_user.id)
                    if not member:
                        continue
                else:
                    continue
            task.position = item.position
            task.status = item.status
    db.commit()
    return {"status": "success", "message": "Tasks reordered successfully."}


@router.put("/{task_id}", response_model=TaskOut)
def update_task_details(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update task details. Users can CRUD assigned/owned tasks. Assignees can update description."""
    task = crud.get_task_by_id(db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Access / permission check: must be owner, assignee, or board manager/lead
    is_owner = (task.user_id == current_user.id)
    is_assignee = (task.assignee_id == current_user.id)
    is_board_admin = False

    if task.board_id:
        from apps.boards.crud import get_board_member
        member = get_board_member(db, board_id=task.board_id, user_id=current_user.id)
        if member and member.role in ("manager", "lead"):
            is_board_admin = True
        elif not member and not is_owner and not is_assignee:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if not is_owner and not is_assignee and not is_board_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify tasks created by or assigned to you."
        )

    # Restricted update for non-owners/non-admins (assignees can update description and status)
    if not is_owner and not is_board_admin:
        task_update.title = None
        task_update.assignee_id = None
        task_update.priority = None

    # Audit tracking when description changes
    if task_update.description is not None and task_update.description != task.description:
        from datetime import datetime
        task_update.description_updated_by = current_user.full_name or current_user.username
        task_update.description_updated_at = datetime.utcnow()

    # If updating status, validate against board columns
    if task_update.status is not None and task.board_id is not None:
        from apps.boards.crud import get_board_by_id
        board = get_board_by_id(db, board_id=task.board_id)
        if board and task_update.status not in board.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{task_update.status}' for board '{board.name}'"
            )

    updated_task = crud.update_task(db, task=task, task_data=task_update)
    return updated_task


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
def delete_task_item(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a task. Requires owner or board lead/manager permissions."""
    task = crud.get_task_by_id(db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Permission check
    if task.user_id != current_user.id:
        if task.board_id:
            from apps.boards.crud import get_board_member
            member = get_board_member(db, board_id=task.board_id, user_id=current_user.id)
            if not member or member.role not in ("manager", "lead"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only task owner or board managers/leads can delete tasks."
                )
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    db.execute(
        update(AIChat)
        .where(AIChat.task_id == task.id)
        .values(task_id=None)
    )
    db.delete(task)
    db.commit()
    return {"status": "success", "message": "Task deleted successfully."}

