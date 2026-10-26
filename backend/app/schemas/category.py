"""Schemas for categories and tags (CM-06)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.base import UUIDPrimaryKey, TimestampMixin


class CategoryBase(BaseModel):
    name: str = Field(..., max_length=200)
    parent_id: str | None = None
    description: str | None = Field(None, max_length=500)
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    parent_id: str | None = None
    description: str | None = Field(None, max_length=500)
    sort_order: int | None = None


class CategoryResponse(CategoryBase):
    id: str
    level: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryTreeNode(CategoryResponse):
    """Category with nested children for tree rendering."""
    children: list["CategoryTreeNode"] = []

    model_config = {"from_attributes": True}


class TagBase(BaseModel):
    name: str = Field(..., max_length=100)


class TagCreate(TagBase):
    pass


class TagResponse(TagBase):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}