"""Shared schema utilities: pagination and generic responses."""

import uuid
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageMeta(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0


class PageResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: list[T]
    meta: PageMeta
