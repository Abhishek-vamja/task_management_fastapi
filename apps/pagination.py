"""Generic pagination response schema for API collection endpoints."""

from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic envelope schema for paginated resource lists.

    Attributes:
        items (list[T]): Page item records.
        total (int): Total number of matching records in database.
        page (int): Current page number (1-indexed).
        limit (int): Maximum records per page.
        pages (int): Total available pages.
    """
    items: list[T]
    total: int
    page: int
    limit: int
    pages: int
