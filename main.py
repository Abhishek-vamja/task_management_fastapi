"""Main application module for the Task Management FastAPI service.

This module initializes the FastAPI application, sets up metadata, configures
database table creation, and registers API routers for authentication, user
management, and task management.
"""

from fastapi import FastAPI

from apps.database import Base, engine

# Import models to ensure they are registered with SQLAlchemy Base metadata
from apps.tasks.models import Task
from apps.users.models import User

# Import routers
from apps.auth.router import router as auth_router
from apps.users.router import router as users_router
from apps.tasks.router import router as tasks_router

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Task Management API",
    description="FastAPI application with JWT Authentication (Register & Login)",
    version="1.0.0",
)

# Register routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(tasks_router)


@app.get("/")
def read_root() -> dict[str, str]:
    """Root endpoint providing welcome message and interactive docs link.

    Returns:
        dict: A dictionary containing welcome message and documentation path.
    """
    return {"message": "Welcome to Task Management API", "docs": "/docs"}
