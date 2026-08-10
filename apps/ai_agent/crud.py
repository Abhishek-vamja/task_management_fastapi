"""CRUD database operations for AI Agent entity."""

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from apps.ai_agent.models import AIChat
# from apps.ai_agent.schemas import TaskCreate


def get_ai_chat_by_id(db: Session, ai_chat_id: int) -> AIChat | None:
    """Retrieve an AI Chat record by its ID.

    Args:
        db (Session): Database session.
        ai_chat_id (int): ID of the AI Chat record.

    Returns:
        AIChat | None: The AI Chat record if found, otherwise None.
    """
    return db.get(AIChat, ai_chat_id)

def get_ai_chat_history_paginated(
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
    total_query = select(func.count()).select_from(AIChat).where(AIChat.user_id == user_id)
    total = db.scalar(total_query) or 0

    # Fetch paginated items
    items_query = (
        select(AIChat)
        .where(AIChat.user_id == user_id)
        .order_by(AIChat.id.desc())
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

def get_ai_chats_by_user(db: Session, user_id: int) -> list[AIChat]:
    """Retrieve all AI Chat records for a specific user.

    Args:
        db (Session): Database session.
        user_id (int): ID of the user whose AI Chat records are to be retrieved.

    Returns:
        list[AIChat]: A list of AI Chat records for the user.
    """
    return db.execute(
        select(AIChat).where(AIChat.user_id == user_id)
    ).scalars().all()

def get_ai_chat_count_by_user(db: Session, user_id: int) -> int:
    """Retrieve the count of AI Chat records for a specific user.

    Args:
        db (Session): Database session.
        user_id (int): ID of the user whose AI Chat record count is to be retrieved.

    Returns:
        int: The count of AI Chat records for the user.
    """
    return db.execute(
        select(func.count(AIChat.id)).where(AIChat.user_id == user_id)
    ).scalar_one()

def create_ai_chat(
    db: Session,
    user_id: int,
    question: str,
    answer: str | None = None,
    ai_answer : str | None = None,
    task_id: int | None = None
) -> AIChat:
    """Create a new AI Chat record in the database.

    Args:
        db (Session): Database session.
        user_id (int): ID of the user creating the chat.
        question (str): The question asked to the AI agent.
        answer (str | None): The answer provided by the AI agent. Defaults to None.
        task_id (int | None): Optional associated task ID. Defaults to None.

    Returns:
        AIChat: The created AI Chat record.
    """
    ai_chat = AIChat(
        user_id=user_id,
        question=question,
        answer=answer,
        ai_answer=ai_answer,
        task_id=task_id
    )
    db.add(ai_chat)
    db.commit()
    db.refresh(ai_chat)
    return ai_chat

def update_ai_chat(
    db: Session,
    ai_chat_id: int,
    answer: str | None = None,
    ai_answer: str | None = None,
    task_id: int | None = None
) -> AIChat:
    """Update an existing AI Chat record in the database.

    Args:
        db (Session): Database session.
        ai_chat_id (int): ID of the AI Chat record to update.
        answer (str | None): The updated answer provided by the AI agent. Defaults to None.
        ai_answer (str | None): The updated AI answer. Defaults to None.
        task_id (int | None): Optional updated associated task ID. Defaults to None.

    Returns:
        AIChat: The updated AI Chat record.
    """
    ai_chat = db.get(AIChat, ai_chat_id)
    if not ai_chat:
        raise ValueError(f"AI Chat with ID {ai_chat_id} not found.")

    if answer is not None:
        ai_chat.answer = answer
    if task_id is not None:
        ai_chat.task_id = task_id
    if ai_answer is not None:
        ai_chat.ai_answer = ai_answer
    db.commit()
    db.refresh(ai_chat)
    return ai_chat

def get_recent_ai_chats(
    db: Session,
    user_id: int,
    limit: int = 10,
    exclude_id: int | None = None
) -> list[AIChat]:
    """Retrieve the most recent completed AI Chat records for a specific user.

    Args:
        db (Session): Database session.
        user_id (int): ID of the user whose AI Chat records are to be retrieved.
        limit (int): Maximum number of records to retrieve (default: 10).
        exclude_id (int): Optional ID to exclude (e.g. the current active chat).

    Returns:
        list[AIChat]: A list of recent AI Chat records for the user.
    """
    query = select(AIChat).where(AIChat.user_id == user_id)
    if exclude_id is not None:
        query = query.where(AIChat.id != exclude_id)
    # Only include chats with non-null answers to prevent empty turns
    query = query.where(AIChat.answer.is_not(None))
    
    return list(db.execute(
        query.order_by(AIChat.id.desc()).limit(limit)
    ).scalars().all())
