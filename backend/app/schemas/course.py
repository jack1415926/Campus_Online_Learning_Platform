"""Schemas for courses and chapters."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.course import ContentType, CourseStatus, Difficulty


class ChapterBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content_type: ContentType = ContentType.video
    content_ref_id: str | None = None
    text_content: str | None = None
    sort_order: int = Field(default=0, ge=0, le=1000000)
    is_required: bool = True
    estimated_minutes: int = 0


class ChapterCreate(ChapterBase):
    pass


class ChapterUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    content_type: ContentType | None = None
    content_ref_id: str | None = None
    text_content: str | None = None
    sort_order: int = Field(default=0, ge=0, le=1000000)
    is_required: bool | None = None
    estimated_minutes: int | None = None


class ChapterResponse(ChapterBase):
    id: str
    course_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    cover_image_url: str | None = Field(None, max_length=1000)
    category_id: str | None = None
    difficulty: Difficulty = Difficulty.beginner
    estimated_minutes: int = 0
    instructor: str | None = Field(None, max_length=100)


class CourseCreate(CourseBase):
    chapters: list[ChapterCreate] = []


class CourseUpdate(BaseModel):
    certificate_exam_id: str | None = Field(None, min_length=36, max_length=36)
    title: str | None = Field(None, max_length=255)
    description: str | None = None
    cover_image_url: str | None = Field(None, max_length=1000)
    category_id: str | None = None
    difficulty: Difficulty | None = None
    estimated_minutes: int | None = None
    instructor: str | None = Field(None, max_length=100)


class CourseResponse(CourseBase):
    certificate_exam_id: str | None = None
    cover_preview_url: str | None = None
    id: str
    status: CourseStatus
    created_by: str | None = None
    created_at: datetime
    review_reason: str | None = None
    is_enrolled: bool = False
    can_manage: bool = False
    can_edit: bool = False
    can_learn: bool = False

    model_config = {"from_attributes": True}


class CourseDetailResponse(CourseResponse):
    """Course with full chapter list."""
    chapters: list[ChapterResponse] = []

    model_config = {"from_attributes": True}


class CourseListFilter(BaseModel):
    status: CourseStatus | None = None
    category_id: str | None = None
    difficulty: Difficulty | None = None
    keyword: str | None = None


class PublishAction(BaseModel):
    """Course publish workflow action."""
    action: Literal["submit_review", "publish", "reject", "archive", "unpublish"]
    reason: str = Field(default="", max_length=1000)
