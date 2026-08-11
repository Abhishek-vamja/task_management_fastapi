"""Main application module for the Task Management FastAPI service.

This module initializes the FastAPI application, sets up metadata, configures
database table creation, and registers API routers for authentication, user
management, and task management.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.database import Base, engine

# Import models to ensure they are registered with SQLAlchemy Base metadata
from apps.tasks.models import Task
from apps.users.models import User
from apps.ai_agent.models import AIChat
from apps.boards.models import Board, BoardMember, Invitation
from apps.organizations.models import Organization, OrganizationMember, OrganizationInvite

# Import routers
from apps.auth.router import router as auth_router
from apps.users.router import router as users_router
from apps.tasks.router import router as tasks_router
from apps.ai_agent.router import router as ai_agent_router
from apps.boards.router import router as boards_router
from apps.organizations.router import router as organizations_router

def auto_migrate_db_columns():
    """Ensure newly added columns exist in production PostgreSQL database tables on startup."""
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            # 1. Add missing columns to boards
            conn.execute(text("ALTER TABLE boards ADD COLUMN IF NOT EXISTS organization_id INTEGER;"))
            
            # 2. Add missing columns to tasks
            conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS organization_id INTEGER;"))
            conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ticket_key VARCHAR;"))
            conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS task_number INTEGER;"))
            
            # 3. Add missing columns to ai_chats
            conn.execute(text("ALTER TABLE ai_chats ADD COLUMN IF NOT EXISTS session_id VARCHAR;"))
            conn.execute(text("ALTER TABLE ai_chats ADD COLUMN IF NOT EXISTS task_id INTEGER;"))
            
            print("[AUTO-MIGRATION] Database schema columns verified and migrated successfully.")
    except Exception as e:
        print(f"[AUTO-MIGRATION WARNING] Could not apply column migrations: {e}")

# Create database tables & run automatic column migrations
Base.metadata.create_all(bind=engine)
auto_migrate_db_columns()

app = FastAPI(
    title="Task Management API",
    description="FastAPI application with JWT Authentication (Register & Login)",
    version="1.0.0",
)

# Configure CORS to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(tasks_router)
app.include_router(ai_agent_router)
app.include_router(boards_router)
app.include_router(organizations_router)


@app.get("/")
def read_root() -> dict[str, str]:
    """Root endpoint providing welcome message and interactive docs link.

    Returns:
        dict: A dictionary containing welcome message and documentation path.
    """
    return {"message": "Welcome to Task Management API", "docs": "/docs"}

@app.get("/health-check")
def read_root() -> dict[str, str]:
    """Root endpoint providing welcome message and interactive docs link.

    Returns:
        dict: A dictionary containing welcome message and documentation path.
    """
    return {"message": "ok", "docs": "/docs"}
