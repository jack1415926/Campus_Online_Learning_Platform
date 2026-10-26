"""Schemas for courses and chapters (CM-01 through CM-07)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.course import ContentType, CourseStatus, Difficulty


class ChapterBase(BaseModel):
    title: str = Field(..., max_length=255)
    content_type: ContentType = ContentType.video
    content_ref_id: str | None = None
    text_content: str | None = None
    sort_order: int = 0
    is_required: bool = True
    estimated_minutes: int = 0
    unlock_condition: dict | None = None


class ChapterCreate(ChapterBase):
    pass


class ChapterUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    content_type: ContentType | None = None
    content_ref_id: str | None = None
    text_content: str | None = None
    sort_order: int | None = None
    is_required: bool | None = None
    estimated_minutes: int | None = None
    unlock_condition: dict | None = None


class ChapterResponse(ChapterBase):
    id: str
    course_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    cover_image_url: str | None = Field(None, max_length=1000)
    category_id: str | None = None
    difficulty: Difficulty = Difficulty.beginner
    estimated_minutes: int = 0
    instructor: str | None = Field(None, max_length=100)


class CourseCreate(CourseBase):
    tag_ids: list[str] = []
    chapters: list[ChapterCreate] = []
    completion_config: dict | None = None


class CourseUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    description: str | None = None
    cover_image_url: str | None = Field(None, max_length=1000)
    category_id: str | None = None
    difficulty: Difficulty | None = None
    estimated_minutes: int | None = None
    instructor: str | None = Field(None, max_length=100)
    tag_ids: list[str] | None = None
    completion_config: dict | None = None


class CourseResponse(CourseBase):
    id: str
    status: CourseStatus
    version: int
    rating: float | None = None
    created_by: str | None = None
    created_at: datetime
    tag_ids: list[str] = []
    completion_config: dict | None = None

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
    """Course publish workflow action (CM-04)."""
    action: str = Field(..., description="submit_review | publish | archive")