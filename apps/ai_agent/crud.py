"""CRUD database operations for AI Agent entity and chat session threads."""

from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from apps.ai_agent.models import AIChat, AIChatSession


def create_ai_session(
    db: Session,
    user_id: int,
    title: str = "New Chat",
    session_id: str | None = None
) -> AIChatSession:
    """Create a new AI chat session thread.

    Args:
        db (Session): Database session.
        user_id (int): Owner user ID.
        title (str): Title/summary of the session thread.
        session_id (str | None): Optional custom session ID (UUID).

    Returns:
        AIChatSession: Created session thread model object.
    """
    if not session_id:
        session_id = f"session_{uuid4().hex[:12]}"
    session_obj = AIChatSession(
        id=session_id,
        user_id=user_id,
        title=title
    )
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)
    return session_obj


def get_user_ai_sessions(db: Session, user_id: int) -> list[AIChatSession]:
    """Retrieve all chat session threads for a user ordered by recent activity.

    Args:
        db (Session): Database session.
        user_id (int): User ID.

    Returns:
        list[AIChatSession]: List of session threads.
    """
    return list(
        db.scalars(
            select(AIChatSession)
            .where(AIChatSession.user_id == user_id)
            .order_by(AIChatSession.updated_at.desc())
        ).all()
    )


def get_ai_session_by_id(db: Session, session_id: str, user_id: int) -> AIChatSession | None:
    """Retrieve a specific AI chat session thread for a user.

    Args:
        db (Session): Database session.
        session_id (str): Session UUID identifier.
        user_id (int): User ID.

    Returns:
        AIChatSession | None: Session thread if found, else None.
    """
    return db.scalars(
        select(AIChatSession).where(
            AIChatSession.id == session_id,
            AIChatSession.user_id == user_id
        )
    ).first()


def delete_ai_session(db: Session, session_id: str, user_id: int) -> bool:
    """Delete an AI chat session thread and all its associated messages.

    Args:
        db (Session): Database session.
        session_id (str): Session UUID identifier.
        user_id (int): Owner user ID.

    Returns:
        bool: True if deleted successfully, False if session not found.
    """
    session_obj = get_ai_session_by_id(db, session_id, user_id)
    if session_obj:
        db.delete(session_obj)
        db.commit()
        return True
    return False


def get_ai_chat_by_id(db: Session, ai_chat_id: int) -> AIChat | None:
    """Retrieve an AI Chat record by its ID."""
    return db.get(AIChat, ai_chat_id)


def get_ai_chat_history_paginated(
    db: Session,
    user_id: int,
    page: int = 1,
    limit: int = 10,
    session_id: str | None = None
) -> dict:
    """Fetch a paginated list of AI chats for a user, optionally filtered by session_id."""
    skip = (page - 1) * limit

    base_query = select(AIChat).where(AIChat.user_id == user_id)
    if session_id:
        base_query = base_query.where(AIChat.session_id == session_id)

    total_query = select(func.count()).select_from(base_query.subquery())
    total = db.scalar(total_query) or 0

    items_query = (
        base_query
        .order_by(AIChat.id.desc())
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


def get_ai_chats_by_user(db: Session, user_id: int) -> list[AIChat]:
    return list(db.scalars(select(AIChat).where(AIChat.user_id == user_id)).all())


def get_ai_chat_count_by_user(db: Session, user_id: int) -> int:
    return db.execute(
        select(func.count(AIChat.id)).where(AIChat.user_id == user_id)
    ).scalar_one()


def create_ai_chat(
    db: Session,
    user_id: int,
    question: str,
    answer: str | None = None,
    ai_answer: str | None = None,
    task_id: int | None = None,
    session_id: str | None = None
) -> AIChat:
    """Create a new AI Chat record in the database."""
    # Ensure active session exists if session_id passed
    if session_id:
        sess = get_ai_session_by_id(db, session_id, user_id)
        if not sess:
            # Auto-create session if not existing
            title_summary = question[:30] if question else "New Chat"
            sess = create_ai_session(db, user_id, title=title_summary, session_id=session_id)

    ai_chat = AIChat(
        user_id=user_id,
        session_id=session_id,
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
    exclude_id: int | None = None,
    session_id: str | None = None
) -> list[AIChat]:
    """Retrieve the most recent completed AI Chat records for a specific user."""
    query = select(AIChat).where(AIChat.user_id == user_id)
    if session_id:
        query = query.where(AIChat.session_id == session_id)
    if exclude_id is not None:
        query = query.where(AIChat.id != exclude_id)
    query = query.where(AIChat.answer.is_not(None))
    
    return list(db.execute(
        query.order_by(AIChat.id.desc()).limit(limit)
    ).scalars().all())
