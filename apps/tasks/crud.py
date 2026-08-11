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
    limit: int = 10,
    organization_id: int | None = None
) -> dict:
    """Fetch a paginated list of tasks belonging to a specific user, optionally filtered by organization_id."""
    skip = (page - 1) * limit

    base_query = select(Task).where((Task.user_id == user_id) | (Task.assignee_id == user_id))
    if organization_id:
        base_query = base_query.where(Task.organization_id == organization_id)

    total_query = select(func.count()).select_from(base_query.subquery())
    total = db.scalar(total_query) or 0

    items_query = (
        base_query
        .order_by(Task.id.desc())
        .offset(skip)
        .limit(limit)
    )
    items = list(db.scalars(items_query).all())
    pages = (total + limit - 1) // limit if total > 0 else 1

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages
    }


def create_task(db: Session, task_data: TaskCreate, user_id: int, organization_id: int | None = None) -> Task:
    """Create a new Task assigned to a specific user ID with custom ticket key."""
    from apps.boards.models import Board
    from apps.organizations import crud as org_crud

    target_org_id = organization_id
    if not target_org_id and task_data.board_id:
        board = db.get(Board, task_data.board_id)
        if board and board.organization_id:
            target_org_id = board.organization_id

    if not target_org_id:
        orgs = org_crud.get_user_organizations(db, user_id)
        if orgs:
            target_org_id = orgs[0].id

    ticket_key = None
    task_num = None
    if target_org_id:
        ticket_key, task_num = org_crud.generate_next_ticket_key(db, target_org_id)

    db_task = Task(
        user_id=user_id,
        title=task_data.title,
        description=task_data.description,
        completed=task_data.completed,
        status=task_data.status,
        priority=task_data.priority,
        tag=task_data.tag,
        assignee_id=task_data.assignee_id,
        board_id=task_data.board_id,
        organization_id=target_org_id,
        ticket_key=ticket_key,
        task_number=task_num,
        position=task_data.position
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def update_task(db: Session, task: Task, task_data) -> Task:
    """Update an existing Task with new data."""
    update_data = task_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


def get_tasks_by_user(db: Session, user_id: int, organization_id: int | None = None) -> list[Task]:
    """Fetch all tasks created by or assigned to a specific user, optionally filtered by organization_id."""
    query = select(Task).where((Task.user_id == user_id) | (Task.assignee_id == user_id))
    if organization_id:
        query = query.where(Task.organization_id == organization_id)
    return list(
        db.scalars(query.order_by(Task.id.desc())).all()
    )